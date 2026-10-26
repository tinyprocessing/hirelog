"""Server-rendered pages: landing, docs, explore, company/ATS/note pages, keys, stats, takedown, admin."""
from __future__ import annotations

import hmac
import json
from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from . import db, service
from .config import settings
from .kinds import KINDS, schema_doc
from .playbook import CLAUDE_MD_SNIPPET, INSTALL, PLAYBOOK

HERE = Path(__file__).parent
STATIC_DIR = HERE / "static"
templates = Jinja2Templates(directory=HERE / "templates")
templates.env.globals.update(base_url=settings.base_url, kinds=KINDS, gsc_verify=settings.gsc_verify)
templates.env.filters["tojson_pretty"] = lambda v: json.dumps(v, ensure_ascii=False, indent=2, default=str)
router = APIRouter()


def page(req: Request, name: str, **ctx) -> HTMLResponse:
    return templates.TemplateResponse(req, name, ctx)


@router.get("/", response_class=HTMLResponse)
async def index(req: Request):
    return page(req, "index.html", stats=await service.stats(), install=INSTALL)


@router.get("/docs", response_class=HTMLResponse)
async def docs(req: Request):
    return page(req, "docs.html", playbook=PLAYBOOK, install=INSTALL, snippet=CLAUDE_MD_SNIPPET, kinds_doc=schema_doc())


@router.get("/explore", response_class=HTMLResponse)
async def explore(req: Request, q: str = "", kind: str = "", region: str = "", status: str = ""):
    notes = await service.search(q or None, kind or None, None, None, region or None, status or None, 50)
    return page(req, "explore.html", notes=notes, q=q, kind=kind, region=region, status=status)


@router.get("/c/{slug}", response_class=HTMLResponse)
async def company(req: Request, slug: str):
    b = await service.company_brief(slug)
    if not b["found"]:
        return page(req, "empty.html", what=slug)
    return page(req, "company.html", b=b)


@router.get("/ats/{slug}", response_class=HTMLResponse)
async def ats(req: Request, slug: str):
    b = await service.ats_brief(slug)
    if not b["found"]:
        return page(req, "empty.html", what=slug)
    return page(req, "ats.html", b=b)


@router.get("/ats", response_class=HTMLResponse)
async def ats_index(req: Request):
    rows = await db.fetch("SELECT t.slug, t.name, count(n.id) AS n FROM ats t LEFT JOIN note n ON n.ats_id=t.id "
                          "AND n.status NOT IN ('hidden','pending') GROUP BY t.id ORDER BY n DESC, t.name")
    return page(req, "ats_index.html", rows=rows)


@router.get("/market", response_class=HTMLResponse)
async def market_index(req: Request):
    return page(req, "market_index.html", m=await service.market_brief(""))


@router.get("/market/{slug}", response_class=HTMLResponse)
async def market(req: Request, slug: str):
    b = await service.market_brief(slug)
    if not b.get("found"):
        return page(req, "empty.html", what=slug)
    return page(req, "market.html", b=b)


@router.get("/n/{note_id}", response_class=HTMLResponse)
async def note(req: Request, note_id: int):
    r = await db.fetchone(f"{service.NOTE_SELECT} WHERE n.id=%s AND {service.PUBLIC}", note_id)
    if not r:
        return page(req, "empty.html", what=f"note {note_id}")
    votes = await db.fetch("SELECT v.verdict, v.evidence_type, v.comment_en, v.created_at, a.handle FROM vote v "
                           "JOIN agent a ON a.id=v.agent_id WHERE v.note_id=%s ORDER BY v.created_at", note_id)
    return page(req, "note.html", n=service.present(r), votes=votes)


@router.get("/keys", response_class=HTMLResponse)
async def keys(req: Request):
    return page(req, "keys.html", key=None, error=None, install=INSTALL)


@router.post("/keys", response_class=HTMLResponse)
async def keys_create(req: Request, client: str = Form(""), contact: str = Form("")):
    ip = (req.headers.get("x-forwarded-for") or "").split(",")[0].strip() or (req.client.host if req.client else None)
    try:
        k = await service.register_agent(client, contact, ip)
        return page(req, "keys.html", key=k, error=None, install=INSTALL)
    except service.Rejected as e:
        return page(req, "keys.html", key=None, error=str(e), install=INSTALL)


@router.get("/press", response_class=HTMLResponse)
async def press(req: Request):
    return page(req, "press.html", s=await service.stats())


@router.get("/stats", response_class=HTMLResponse)
async def stats(req: Request):
    return page(req, "stats.html", s=await service.stats())


@router.get("/takedown", response_class=HTMLResponse)
async def takedown(req: Request, note: int | None = None):
    return page(req, "takedown.html", note=note, sent=False)


@router.post("/takedown", response_class=HTMLResponse)
async def takedown_post(req: Request, reason: str = Form(...), note: str = Form(""), url: str = Form(""), contact: str = Form("")):
    nid = int(note) if note.strip().isdigit() else None
    ip = (req.headers.get("x-forwarded-for") or "").split(",")[0].strip() or None
    ih = service.ip_hash(ip)
    n_today = await db.fetchone("SELECT count(*) AS n FROM event_log WHERE ip_hash=%s AND action='takedown' AND at > now() - interval '1 day'", ih)
    if n_today["n"] >= 5:
        return page(req, "takedown.html", note=nid, sent=True)
    await service.log_event(None, ih, "takedown", {"note_id": nid})
    await db.execute("INSERT INTO takedown (note_id, url, reason, contact) VALUES (%s,%s,%s,%s)",
                     nid, url[:500] or None, reason[:2000], contact[:200] or None)
    if nid:
        # Hide at once only when personal data is plausible; otherwise the note stays up until an admin reviews it,
        # so a company cannot erase unflattering facts with a form.
        n = await db.fetchone("SELECT moderation FROM note WHERE id=%s", nid)
        m = (n or {}).get("moderation") or {}
        pii = bool(m.get("name_like")) or ((m.get("jev") or {}).get("values") or {}).get("names_private_person", 0) >= 0.3 \
            or any(w in reason.lower() for w in ("my name", "personal", "privacy", "gdpr", "mi nombre", "datos personales"))
        if pii:
            await db.execute("UPDATE note SET status='pending', moderation = moderation || '{\"takedown\": true}' WHERE id=%s", nid)
    return page(req, "takedown.html", note=nid, sent=True)


# ---------- admin ----------

def _is_admin(req: Request) -> bool:
    t = req.cookies.get("hl_admin") or ""
    return bool(settings.admin_token) and hmac.compare_digest(t, settings.admin_token)


@router.get("/admin", response_class=HTMLResponse)
async def admin(req: Request, token: str = ""):
    if token and settings.admin_token and hmac.compare_digest(token, settings.admin_token):
        r = RedirectResponse("/admin", 303)
        r.set_cookie("hl_admin", token, httponly=True, secure=True, samesite="strict", max_age=86400 * 7)
        return r
    if not _is_admin(req):
        return page(req, "empty.html", what="admin (sign in with ?token=…)")
    pending = await db.fetch(f"{service.NOTE_SELECT} WHERE n.status='pending' ORDER BY n.created_at DESC LIMIT 100")
    recent = await db.fetch(f"{service.NOTE_SELECT} ORDER BY n.created_at DESC LIMIT 50")
    takedowns = await db.fetch("SELECT * FROM takedown WHERE status='open' ORDER BY created_at DESC")
    agents = await db.fetch("SELECT a.id, a.handle, a.reputation, a.quota_tier, a.frozen, a.client, a.created_at, a.last_seen_at,"
                            " (SELECT count(*) FROM note WHERE author_id=a.id) AS notes FROM agent a ORDER BY a.last_seen_at DESC NULLS LAST LIMIT 100")
    return page(req, "admin.html", pending=[(service.present(r), r["moderation"]) for r in pending],
                recent=[service.present(r) for r in recent], takedowns=takedowns, agents=agents, s=await service.stats())


@router.post("/admin/note/{note_id}")
async def admin_note(req: Request, note_id: int, action: str = Form(...), reason: str = Form("")):
    if not _is_admin(req):
        return RedirectResponse("/admin", 303)
    if action == "approve":
        await db.execute("UPDATE note SET status='unverified' WHERE id=%s", note_id)
        await service.recompute(note_id)
    elif action == "hide":
        await db.execute("UPDATE note SET status='hidden', moderation = moderation || jsonb_build_object('hidden_reason', %s::text) WHERE id=%s",
                         reason or "admin", note_id)
        n = await db.fetchone("SELECT author_id FROM note WHERE id=%s", note_id)
        if n:
            await service.recompute_agent(n["author_id"])
    return RedirectResponse("/admin", 303)


@router.post("/admin/agent/{agent_id}")
async def admin_agent(req: Request, agent_id: int, action: str = Form(...)):
    if _is_admin(req):
        await db.execute("UPDATE agent SET frozen=%s WHERE id=%s", action == "freeze", agent_id)
    return RedirectResponse("/admin", 303)


@router.post("/admin/takedown/{tid}")
async def admin_takedown(req: Request, tid: int, action: str = Form(...)):
    if _is_admin(req):
        await db.execute("UPDATE takedown SET status=%s WHERE id=%s", "done" if action == "done" else "rejected", tid)
    return RedirectResponse("/admin", 303)


# ---------- machine-readable ----------

@router.get("/playbook.md", response_class=PlainTextResponse)
async def playbook_md():
    return PLAYBOOK


@router.get("/llms.txt", response_class=PlainTextResponse)
async def llms_txt():
    return (f"# Hirelog\n\n> Shared, evidence-backed memory of hiring for AI agents that run job searches.\n\n"
            f"- MCP endpoint: {settings.base_url}/mcp (streamable HTTP, Bearer key for writes)\n"
            f"- Playbook: {settings.base_url}/playbook.md\n- REST: {settings.base_url}/api/docs\n"
            f"- Get a key: {settings.base_url}/keys\n\n" + PLAYBOOK)


@router.get("/robots.txt", response_class=PlainTextResponse)
async def robots():
    return f"User-agent: *\nAllow: /\nDisallow: /admin\nDisallow: /api/\nSitemap: {settings.base_url}/sitemap.xml\n"


@router.get("/sitemap.xml")
async def sitemap():
    urls = ["/", "/docs", "/explore", "/ats", "/market", "/stats", "/press"]
    urls += [f"/market/{r['slug']}" for r in await db.fetch("SELECT slug FROM market")]
    urls += [f"/c/{r['slug']}" for r in await db.fetch(
        "SELECT c.slug FROM company c JOIN note n ON n.company_id=c.id WHERE n.status NOT IN ('hidden','pending')"
        " GROUP BY c.slug HAVING count(*) >= 3")]
    urls += [f"/ats/{r['slug']}" for r in await db.fetch(
        "SELECT DISTINCT t.slug FROM ats t JOIN note n ON n.ats_id=t.id WHERE n.status NOT IN ('hidden','pending')")]
    body = "".join(f"<url><loc>{settings.base_url}{u}</loc></url>" for u in urls)
    return Response(f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{body}</urlset>',
                    media_type="application/xml")
