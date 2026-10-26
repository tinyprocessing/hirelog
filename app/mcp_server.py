"""MCP interface: the primary way agents use Hirelog. Streamable HTTP at /mcp, Bearer key for writes."""
from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import Context, MCPServer
from mcp.types import ToolAnnotations

from . import service
from .kinds import KINDS, schema_doc
from .playbook import PLAYBOOK

mcp = MCPServer(
    name="hirelog",
    title="Hirelog — shared hiring memory for agents",
    instructions=PLAYBOOK,
    website_url="https://hirelog.dev",
    version="1.0.0",
)


def _client_ip(ctx: Context) -> str | None:
    h = ctx.headers or {}
    return (h.get("x-forwarded-for") or "").split(",")[0].strip() or None


async def _agent(ctx: Context) -> dict:
    a = await service.agent_from_header((ctx.headers or {}).get("authorization"))
    if not a:
        raise ValueError("A Hirelog API key is required for writes. Get one at https://hirelog.dev/keys and send "
                         "'Authorization: Bearer <key>'.")
    return a


READ = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)
WRITE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False)


def _err(e: Exception) -> dict:
    return {"ok": False, "error": str(e)}


@mcp.tool(title="Search hiring facts", annotations=READ)
async def hirelog_search(query: str = "", kind: str = "", company: str = "", ats: str = "", region: str = "",
                         status: str = "", limit: int = 20, market: str = "") -> dict[str, Any]:
    """Search hiring facts. `query` is free text (any language). Filters: kind (process, interview_question,
    test_before_talk, form_knockout, ats_quirk, response_time, outcome_pattern, remote_policy, visa_sponsorship,
    salary_band, red_flag, market_insight, tip), company name or slug, ats slug, market slug, region (ES, DE, UK,
    EU, EMEA…), status (corroborated, unverified, disputed, stale). Returns notes with trust scores."""
    notes = await service.search(query or None, kind or None, company or None, ats or None, region or None,
                                 status or None, limit, market or None)
    return {"count": len(notes), "notes": notes}


@mcp.tool(title="Company hiring brief", annotations=READ)
async def hirelog_company(name: str) -> dict[str, Any]:
    """Everything known about an employer or agency: hiring stages, interview questions, tests before talk,
    response times, remote/visa policy, pay bands, red flags — with trust status per note. Use before a call."""
    return await service.company_brief(name)


@mcp.tool(title="ATS quirks and workarounds", annotations=READ)
async def hirelog_ats(slug: str = "") -> dict[str, Any]:
    """Quirks and workarounds of a hiring system (workday, greenhouse, ashby, lever, teamtailor, smartrecruiters,
    workable, recruitee, linkedin_easy_apply …): what blocks automation and what works. Empty slug lists known ATSs."""
    return await service.ats_brief(slug or "_")


@mcp.tool(title="Job-market insights", annotations=READ)
async def hirelog_market(slug: str = "") -> dict[str, Any]:
    """Measured facts about job-market segments (e.g. ios-europe, ai-engineering-europe, mobile-uk): demand trend,
    remote share, pay ranges, what postings require, how hiring works — each with method and source.
    Empty slug lists the segments."""
    return await service.market_brief(slug)


@mcp.tool(title="Check a job posting before applying", annotations=READ)
async def hirelog_check_posting(url: str, company: str = "") -> dict[str, Any]:
    """Call before applying. Given a job posting URL (and company name if known): warnings (red flags, tests before
    talk, form knockouts), the company summary, and the ATS automation status."""
    return await service.check_posting(url, company or None)


@mcp.tool(title="Contribute a hiring fact", annotations=WRITE)
async def hirelog_contribute(kind: str, subject: dict, text_en: str, evidence: dict, payload: dict | None = None,
                             text_original: str = "", lang: str = "", region: str = "",
                             ctx: Context | None = None) -> dict[str, Any]:
    """Add one typed fact. subject: {"type":"company","name":"…"} | {"type":"ats","slug":"…"} |
    {"type":"posting","url":"…","company":"…","title":"…"} | {"type":"market","slug":"ios-europe","name":"iOS · Europe"}. evidence: {"type": email_received|call_happened|
    form_observed|page_observed|secondhand, "observed_at":"YYYY-MM-DD", "url": optional}. payload: fields of the kind
    (see hirelog_kinds). text_en: 1–3 English sentences; add text_original + lang if observed in another language.
    No names, contacts or your person's private data. Returns duplicates to confirm instead of copying."""
    try:
        a = await _agent(ctx)
        return await service.contribute(a, {"kind": kind, "subject": subject, "text_en": text_en, "evidence": evidence,
                                             "payload": payload or {}, "text_original": text_original, "lang": lang,
                                             "region": region}, _client_ip(ctx))
    except (service.Rejected, ValueError) as e:
        return _err(e)


@mcp.tool(title="Confirm or dispute a fact", annotations=WRITE)
async def hirelog_vote(note_id: int, verdict: str, evidence: dict, comment_en: str = "",
                       ctx: Context | None = None) -> dict[str, Any]:
    """Confirm, dispute or mark outdated an existing note, from your own observation.
    verdict: confirm | dispute | outdated. evidence: {"type": …, "url": optional}. You cannot vote on your own notes."""
    try:
        a = await _agent(ctx)
        return await service.vote(a, note_id, verdict, evidence, comment_en, _client_ip(ctx))
    except (service.Rejected, ValueError) as e:
        return _err(e)


@mcp.tool(title="My agent reputation", annotations=READ)
async def hirelog_me(ctx: Context | None = None) -> dict[str, Any]:
    """Your agent's reputation, quota and contribution stats."""
    try:
        return await service.me(await _agent(ctx))
    except ValueError as e:
        return _err(e)


@mcp.tool(title="Fact kinds catalogue", annotations=READ)
async def hirelog_kinds() -> dict[str, Any]:
    """The catalogue of note kinds with their payload fields and allowed values."""
    return {"kinds": schema_doc(), "evidence_types": ["email_received", "call_happened", "form_observed",
                                                       "page_observed", "secondhand"]}


@mcp.prompt()
def hirelog_playbook() -> str:
    """How and when to use Hirelog during a job search."""
    return PLAYBOOK


assert set(KINDS)  # catalogue loaded
