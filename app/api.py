"""REST API (/api/v1) — mirrors the MCP tools for scripts and the web UI."""
from __future__ import annotations

from fastapi import APIRouter, Body, Header, HTTPException, Request
from fastapi.responses import PlainTextResponse

from . import service
from .kinds import schema_doc
from .playbook import PLAYBOOK

router = APIRouter(prefix="/api/v1", tags=["api"])


def _ip(req: Request) -> str | None:
    return (req.headers.get("x-forwarded-for") or "").split(",")[0].strip() or (req.client.host if req.client else None)


async def _need_agent(authorization: str | None) -> dict:
    a = await service.agent_from_header(authorization)
    if not a:
        raise HTTPException(401, "API key required: Authorization: Bearer <key> (get one at /keys)")
    return a


@router.get("/search")
async def search(q: str = "", kind: str = "", company: str = "", ats: str = "", region: str = "", status: str = "", limit: int = 20):
    notes = await service.search(q or None, kind or None, company or None, ats or None, region or None, status or None, limit)
    return {"count": len(notes), "notes": notes}


@router.get("/companies/{name}")
async def company(name: str):
    return await service.company_brief(name)


@router.get("/ats/{slug}")
async def ats(slug: str):
    return await service.ats_brief(slug)


@router.get("/check")
async def check(url: str, company: str = ""):
    return await service.check_posting(url, company or None)


@router.post("/notes")
async def contribute(req: Request, body: dict = Body(...), authorization: str | None = Header(None)):
    a = await _need_agent(authorization)
    try:
        return await service.contribute(a, body, _ip(req))
    except service.Rejected as e:
        raise HTTPException(422, str(e)) from None


@router.post("/notes/{note_id}/votes")
async def vote(note_id: int, req: Request, body: dict = Body(...), authorization: str | None = Header(None)):
    a = await _need_agent(authorization)
    try:
        return await service.vote(a, note_id, body.get("verdict", ""), body.get("evidence") or {}, body.get("comment_en"), _ip(req))
    except service.Rejected as e:
        raise HTTPException(422, str(e)) from None


@router.get("/me")
async def me(authorization: str | None = Header(None)):
    return await service.me(await _need_agent(authorization))


@router.post("/keys")
async def keys(req: Request, body: dict = Body(default={})):
    try:
        return await service.register_agent(body.get("client"), body.get("contact"), _ip(req))
    except service.Rejected as e:
        raise HTTPException(429, str(e)) from None


@router.get("/kinds")
async def kinds():
    return {"kinds": schema_doc()}


@router.get("/stats")
async def stats():
    return await service.stats()


@router.get("/playbook.md", response_class=PlainTextResponse)
async def playbook():
    return PLAYBOOK
