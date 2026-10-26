"""Client for the embed service (vectors + reranking). Every call degrades to None: search then falls back to full text."""
from __future__ import annotations

import logging

import httpx

from .config import settings

log = logging.getLogger("hirelog.embed")
_client: httpx.AsyncClient | None = None


def enabled() -> bool:
    return bool(settings.embed_url)


def _http() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(base_url=settings.embed_url, timeout=httpx.Timeout(4.0, connect=1.0))
    return _client


async def vectors(texts: list[str]) -> list[list[float]] | None:
    if not enabled() or not texts:
        return None
    try:
        r = await _http().post("/embed", json={"texts": texts})
        r.raise_for_status()
        return r.json()["vectors"]
    except Exception as e:  # noqa: BLE001 — search must keep working without the model
        log.warning("embed failed: %s", e)
        return None


async def rerank(query: str, docs: list[str]) -> list[float] | None:
    if not enabled() or not docs:
        return None
    try:
        r = await _http().post("/rerank", json={"query": query, "docs": docs})
        r.raise_for_status()
        return r.json()["scores"]
    except Exception as e:  # noqa: BLE001
        log.warning("rerank failed: %s", e)
        return None


def to_pg(v: list[float]) -> str:
    """pgvector text literal: '[0.1,0.2,...]'."""
    return "[" + ",".join(f"{x:.6f}" for x in v) + "]"


def note_text(kind: str, subject: str, text_en: str, text_original: str | None) -> str:
    """What we embed for a note: kind and subject give context, both languages give multilingual recall."""
    parts = [f"{kind.replace('_', ' ')} · {subject}", text_en]
    if text_original:
        parts.append(text_original)
    return "\n".join(parts)
