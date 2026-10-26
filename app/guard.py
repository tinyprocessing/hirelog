"""Edge protection inside the app: per-IP rate limits, automatic IP bans for sustained flooding, cache headers.

Limits are per worker process (token buckets in memory) — enough to stop scripted abuse without a Redis dependency.
Caddy in front strips spoofed X-Forwarded-For, so the first hop is the real client.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque

from starlette.types import ASGIApp, Receive, Scope, Send

from . import service

# Per process; 2 replicas × 2 workers ⇒ ~4× these per IP in total (~240 reads, ~360 MCP, ~40 writes a minute).
LIMITS = {"read": (60, 60), "mcp": (90, 60), "write": (10, 60)}      # (requests, per seconds)
FLOOD_429 = 25                                                           # 429s in 10 min → 1 h IP ban
PUBLIC_CACHE = ("/", "/docs", "/explore", "/ats", "/market", "/stats", "/llms.txt", "/playbook.md", "/robots.txt", "/sitemap.xml")
PUBLIC_PREFIX = ("/c/", "/ats/", "/market/", "/n/")


class Guard:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.buckets: dict[tuple[str, str], list[float]] = {}
        self.rejects: dict[str, deque] = defaultdict(deque)

    @staticmethod
    def _cls(method: str, path: str) -> str:
        if path.startswith("/mcp"):
            return "mcp"
        if method == "POST":
            return "write"
        return "read"

    def _allow(self, key: tuple[str, str]) -> bool:
        cap, per = LIMITS[key[1]]
        now = time.monotonic()
        tokens, last = self.buckets.get(key, [float(cap), now])
        tokens = min(cap, tokens + (now - last) * cap / per)
        if tokens < 1:
            self.buckets[key] = [tokens, now]
            return False
        self.buckets[key] = [tokens - 1, now]
        if len(self.buckets) > 50_000:            # bounded memory
            self.buckets.clear()
        return True

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        path, method = scope.get("path", "/"), scope.get("method", "GET")
        if path == "/health" or path.startswith("/static/"):
            return await self.app(scope, receive, send)
        headers = dict(scope.get("headers") or [])
        ip = (headers.get(b"x-forwarded-for", b"").decode().split(",")[0].strip()
              or (scope.get("client") or ("", 0))[0])
        ih = service.ip_hash(ip) or "unknown"
        if await service.is_banned("ip", ih):
            return await _plain(send, 403, "Blocked for abuse. If this is a mistake, wait an hour or use /takedown to contact us.")
        cls = self._cls(method, path)
        if not self._allow((ih, cls)):
            q = self.rejects[ih]
            now = time.monotonic()
            q.append(now)
            while q and now - q[0] > 600:
                q.popleft()
            if len(q) >= FLOOD_429:
                await service.ban("ip", ih, f"auto: {len(q)} rate-limit hits in 10 min", 1)
                q.clear()
            return await _plain(send, 429, "Too many requests — slow down.", {"retry-after": "20"})

        cacheable = method == "GET" and (path in PUBLIC_CACHE or path.startswith(PUBLIC_PREFIX))
        api_get = method == "GET" and path.startswith("/api/v1/") and not path.startswith("/api/v1/me")

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                hs = list(message.get("headers") or [])
                names = {k.lower() for k, _ in hs}
                if b"cache-control" not in names:
                    value = (b"public, max-age=60, stale-while-revalidate=600" if cacheable else
                             b"public, max-age=30" if api_get else b"no-store")
                    hs.append((b"cache-control", value))
                message["headers"] = hs
            await send(message)

        return await self.app(scope, receive, send_wrapper)


async def _plain(send: Send, status: int, text: str, extra: dict | None = None) -> None:
    hs = [(b"content-type", b"text/plain; charset=utf-8"), (b"cache-control", b"no-store")]
    hs += [(k.encode(), v.encode()) for k, v in (extra or {}).items()]
    await send({"type": "http.response.start", "status": status, "headers": hs})
    await send({"type": "http.response.body", "body": text.encode()})
