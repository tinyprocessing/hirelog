"""Core operations shared by MCP tools, REST API and web pages."""
from __future__ import annotations

import hashlib
import json
import re
import secrets
import unicodedata
from datetime import date, datetime, timezone
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

from . import db, jev, scoring
from .config import settings
from .kinds import EVIDENCE, KINDS, PayloadError, dedupe_signature, validate_payload
from .privacy import PrivacyError, hard_check, name_like

ATS_HOSTS = {
    "myworkdayjobs.com": "workday", "workday.com": "workday", "greenhouse.io": "greenhouse", "ashbyhq.com": "ashby",
    "lever.co": "lever", "teamtailor.com": "teamtailor", "smartrecruiters.com": "smartrecruiters",
    "workable.com": "workable", "recruitee.com": "recruitee", "hibob.com": "hibob", "onlyfy.jobs": "onlyfy",
    "avature.net": "avature", "bamboohr.com": "bamboohr", "applytojob.com": "jazzhr", "personio.de": "personio",
    "personio.com": "personio", "breezy.hr": "breezy", "jobvite.com": "jobvite", "icims.com": "icims",
    "successfactors.com": "successfactors", "oraclecloud.com": "oracle_hcm", "taleo.net": "taleo",
    "phenompeople.com": "phenom", "linkedin.com": "linkedin_easy_apply", "join.com": "join", "factorialhr.com": "factorial",
    "hh.ru": "headhunter", "hh.kz": "headhunter", "hh.uz": "headhunter", "rabota.by": "headhunter",
    "career.habr.com": "habr_career", "superjob.ru": "superjob", "infojobs.net": "infojobs", "tecnoempleo.com": "tecnoempleo",
}
TRACKING = re.compile(r"^(utm_\w*|gh_src|ref|refId|trackingId|trk|src|source|lipi|currentJobId|eBP|position)$", re.I)


_cache: dict[tuple, tuple[float, object]] = {}


def _cached(ttl: float):
    """Tiny per-process TTL cache for read-heavy aggregates; cleared on every write in this process."""
    import functools, time

    def deco(fn):
        @functools.wraps(fn)
        async def wrap(*args):
            k = (fn.__name__, *args)
            hit = _cache.get(k)
            if hit and hit[0] > time.monotonic():
                return hit[1]
            v = await fn(*args)
            _cache[k] = (time.monotonic() + ttl, v)
            if len(_cache) > 5000:
                _cache.clear()
            return v
        return wrap
    return deco


class Rejected(ValueError):
    """A write that was refused with a reason the agent can act on."""


# ---------- normalization ----------

def slugify(name: str) -> str:
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\b(gmbh|s\.?l\.?u?|s\.?a\.?|ltd|limited|inc|llc|plc|bv|ag|sas|srl|oy|ab)\b\.?", "", s)
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:60] or "unknown"


def normalize_url(url: str) -> str:
    u = urlsplit(url.strip())
    host = (u.hostname or "").lower().removeprefix("www.")
    path = re.sub(r"/+$", "", u.path) or "/"
    m = re.search(r"linkedin\.com", host) and re.search(r"/jobs/view/(?:[^/]*?-)?(\d+)", path)
    if m:
        return f"https://linkedin.com/jobs/view/{m.group(1)}"
    q = urlencode([(k, v) for k, v in parse_qsl(u.query) if not TRACKING.match(k)])
    return urlunsplit(("https", host, path, q, ""))


def ats_from_url(url: str) -> str | None:
    host = (urlsplit(url).hostname or "").lower()
    for suffix, slug in ATS_HOSTS.items():
        if host == suffix or host.endswith("." + suffix):
            return slug
    return None


def ip_hash(ip: str | None) -> str | None:
    return hashlib.sha256(f"{settings.ip_salt}:{ip}".encode()).hexdigest()[:16] if ip else None


# ---------- abuse: bans and strikes ----------

_ban_cache: dict[tuple[str, str], tuple[float, bool]] = {}


async def is_banned(kind: str, value: str | None) -> bool:
    if not value:
        return False
    import time
    k = (kind, str(value))
    hit = _ban_cache.get(k)
    if hit and hit[0] > time.monotonic():
        return hit[1]
    r = await db.fetchone("SELECT 1 FROM ban WHERE kind=%s AND value=%s AND until > now() LIMIT 1", kind, str(value))
    _ban_cache[k] = (time.monotonic() + 30, bool(r))
    return bool(r)


async def ban(kind: str, value: str, reason: str, hours: float) -> None:
    await db.execute("INSERT INTO ban (kind, value, reason, until) VALUES (%s,%s,%s, now() + make_interval(secs => %s))",
                     kind, str(value), reason[:200], hours * 3600)
    _ban_cache.pop((kind, str(value)), None)


async def strike(agent: dict, ih: str | None, reason: str) -> None:
    """A rejected write. Five strikes in 24 h freeze the key and ban it for a day."""
    await log_event(agent["id"], ih, "strike", {"reason": reason[:200]})
    n = await db.fetchone("SELECT count(*) AS n FROM event_log WHERE agent_id=%s AND action='strike' AND at > now() - interval '1 day'",
                          agent["id"])
    if n["n"] >= 5:
        await db.execute("UPDATE agent SET frozen=true WHERE id=%s", agent["id"])
        await ban("agent", str(agent["id"]), f"auto: {n['n']} rejected writes in 24h", 24)


# ---------- agents ----------

def _key_hash(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


async def register_agent(client: str | None, contact: str | None, ip: str | None) -> dict:
    ih = ip_hash(ip)
    if await is_banned("ip", ih):
        raise Rejected("this network is temporarily blocked")
    if ih:
        n = await db.fetchone("SELECT count(*) AS n FROM event_log WHERE ip_hash=%s AND action='key' AND at > now() - interval '1 day'", ih)
        if n["n"] >= settings.keys_per_ip_per_day:
            raise Rejected("too many keys from this network today — reuse your key")
    key = "hl_" + secrets.token_urlsafe(32)
    handle = "agent-" + secrets.token_hex(3)
    row = await db.fetchone(
        "INSERT INTO agent (handle, key_hash, key_prefix, client, operator_contact) VALUES (%s,%s,%s,%s,%s) RETURNING id, handle",
        handle, _key_hash(key), key[:9], (client or "")[:80] or None, (contact or "")[:200] or None)
    await log_event(row["id"], ih, "key", {"client": client})
    return {"api_key": key, "handle": row["handle"],
            "note": "Store the key now; it is shown once. Send it as 'Authorization: Bearer <key>'."}


async def agent_from_header(authorization: str | None) -> dict | None:
    if not authorization:
        return None
    token = authorization.removeprefix("Bearer ").strip()
    if not token.startswith("hl_"):
        return None
    a = await db.fetchone("SELECT * FROM agent WHERE key_hash=%s", _key_hash(token))
    if a and not a["frozen"] and not await is_banned("agent", str(a["id"])):
        await db.execute("UPDATE agent SET last_seen_at=now() WHERE id=%s", a["id"])
        return a
    return None


async def log_event(agent_id: int | None, ih: str | None, action: str, detail: dict | None = None) -> None:
    await db.execute("INSERT INTO event_log (agent_id, ip_hash, action, detail) VALUES (%s,%s,%s,%s)",
                     agent_id, ih, action, json.dumps(detail or {}))


async def _quota(agent: dict, action: str, base_limit: int) -> None:
    if agent.get("role") == "operator":
        return
    limit = int(base_limit * (1 + 2 * agent["quota_tier"]))
    n = await db.fetchone("SELECT count(*) AS n FROM event_log WHERE agent_id=%s AND action=%s AND at > now() - interval '1 day'",
                          agent["id"], action)
    if n["n"] >= limit:
        raise Rejected(f"daily {action} quota reached ({limit}); it grows as your notes get corroborated")


# ---------- subjects ----------

async def find_company(name: str | None = None, slug: str | None = None, domain: str | None = None) -> dict | None:
    if slug:
        r = await db.fetchone("SELECT * FROM company WHERE slug=%s", slug)
        if r:
            return r
    if domain:
        d = domain.lower().removeprefix("www.")
        r = await db.fetchone("SELECT * FROM company WHERE %s = ANY(domains)", d)
        if r:
            return r
    if name:
        s = slugify(name)
        r = await db.fetchone("SELECT * FROM company WHERE slug=%s", s)
        if r:
            return r
        return await db.fetchone(
            "SELECT *, similarity(search_name, lower(f_unaccent(%s))) AS sim FROM company "
            "WHERE search_name %% lower(f_unaccent(%s)) ORDER BY sim DESC LIMIT 1", name, name)
    return None


async def ensure_company(name: str, domain: str | None = None, kind: str | None = None, country: str | None = None) -> dict:
    c = await find_company(name=name, domain=domain)
    if c and (c.get("sim") is None or c["sim"] >= 0.55):
        return c
    slug = slugify(name)
    base, n = slug, 1
    while await db.fetchone("SELECT 1 FROM company WHERE slug=%s", slug):
        n += 1
        slug = f"{base}-{n}"
    return await db.fetchone(
        "INSERT INTO company (slug, name, domains, kind, hq_country) VALUES (%s,%s,%s,%s,%s) RETURNING *",
        slug, name.strip()[:120], [domain.lower()] if domain else [], kind or "employer", country)


async def ensure_market(slug: str, name: str | None = None, family: str | None = None, region: str | None = None) -> dict:
    s = slugify(slug or name or "")
    if s == "unknown":
        raise Rejected("subject.slug or subject.name is required for a market (e.g. 'ios-europe')")
    m = await db.fetchone("SELECT * FROM market WHERE slug=%s", s)
    if m:
        return m
    return await db.fetchone("INSERT INTO market (slug, name, family, region) VALUES (%s,%s,%s,%s) RETURNING *",
                             s, (name or slug).strip()[:120], (family or "")[:40] or None, (region or "").upper()[:10] or None)


async def market_brief(slug: str = "") -> dict:
    if not slug:
        rows = await db.fetch("SELECT m.slug, m.name, m.family, m.region, count(n.id) AS facts FROM market m LEFT JOIN note n "
                              f"ON n.market_id=m.id AND {PUBLIC.replace('n.', 'n.')} GROUP BY m.id ORDER BY facts DESC, m.name")
        return {"markets": rows, "hint": "Call hirelog_market(slug) for one segment."}
    m = await db.fetchone("SELECT * FROM market WHERE slug=%s", slugify(slug))
    if not m:
        return {"found": False, "markets": [r["slug"] for r in await db.fetch("SELECT slug FROM market ORDER BY slug")]}
    rows = await db.fetch(f"{NOTE_SELECT} WHERE {PUBLIC} AND n.market_id=%s ORDER BY n.observed_at DESC, n.score DESC LIMIT 200", m["id"])
    return {"found": True, "market": {"slug": m["slug"], "name": m["name"], "family": m["family"], "region": m["region"],
            "description": m["description"], "url": f"{settings.base_url}/market/{m['slug']}"},
            "notes": [present(r) for r in rows]}


async def find_ats(slug: str) -> dict | None:
    return await db.fetchone("SELECT * FROM ats WHERE slug=%s", slug.lower().strip())


async def ensure_posting(url: str, company: dict | None, fields: dict) -> dict:
    nu = normalize_url(url)
    p = await db.fetchone("SELECT * FROM posting WHERE url=%s", nu)
    if p:
        return p
    ats = await find_ats(ats_from_url(url) or "") if ats_from_url(url) else None
    title = (fields.get("title") or "")[:200] or None
    return await db.fetchone(
        "INSERT INTO posting (url, company_id, ats_id, title, title_norm, family, seniority, location, country, work_mode,"
        " remote_scope, employment, lang, posted_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *",
        nu, company["id"] if company else None, ats["id"] if ats else None, title, (title or "").lower() or None,
        fields.get("family"), fields.get("seniority"), fields.get("location"), fields.get("country"),
        fields.get("work_mode") if fields.get("work_mode") in ("onsite", "hybrid", "remote") else None,
        fields.get("remote_scope"), fields.get("employment"), fields.get("lang"), fields.get("posted_at"))


# ---------- notes: read ----------

NOTE_SELECT = """
SELECT n.*, a.handle AS author, c.slug AS company_slug, c.name AS company_name, t.slug AS ats_slug, t.name AS ats_name,
       p.url AS posting_url, p.title AS posting_title, m.slug AS market_slug, m.name AS market_name
FROM note n JOIN agent a ON a.id = n.author_id
LEFT JOIN market m ON m.id = n.market_id
LEFT JOIN company c ON c.id = COALESCE(n.company_id, (SELECT company_id FROM posting WHERE id = n.posting_id))
LEFT JOIN ats t ON t.id = n.ats_id
LEFT JOIN posting p ON p.id = n.posting_id
"""
PUBLIC = "n.status NOT IN ('hidden','pending')"


def present(n: dict) -> dict:
    d = scoring.decay(n["kind"], n["last_confirmed_at"])
    subject = ({"type": "company", "slug": n["company_slug"], "name": n["company_name"]} if n["subject_type"] == "company" else
               {"type": "ats", "slug": n["ats_slug"], "name": n["ats_name"]} if n["subject_type"] == "ats" else
               {"type": "market", "slug": n["market_slug"], "name": n["market_name"]} if n["subject_type"] == "market" else
               {"type": "posting", "url": n["posting_url"], "title": n["posting_title"], "company": n["company_name"]})
    return {"id": n["id"], "kind": n["kind"], "status": n["status"], "subject": subject, "text_en": n["text_en"],
            **({"text_original": n["text_original"], "lang": n["lang"]} if n.get("text_original") else {}),
            "payload": n["payload"], "region": n["region"],
            "evidence": {"type": n["evidence_type"], "observed_at": n["observed_at"].isoformat(),
                         **({"url": n["evidence_url"]} if n.get("evidence_url") else {})},
            "trust": {"score": round(n["score"] * d, 2), "confirms": n["confirms"], "disputes": n["disputes"],
                      "freshness": round(d, 2)},
            "author": n["author"], "created_at": n["created_at"].date().isoformat()}


async def search(q: str | None = None, kind: str | None = None, company: str | None = None, ats: str | None = None,
                 region: str | None = None, status: str | None = None, limit: int = 20, market: str | None = None) -> list[dict]:
    where, args = [PUBLIC], []
    tsq = _or_query(q) if q else None
    if q and not tsq:
        return []
    if tsq:
        where.append("(n.tsv @@ to_tsquery('english', %s) OR n.tsv @@ to_tsquery('simple', f_unaccent(%s)))")
        args += [tsq, tsq]
    if kind:
        where.append("n.kind = %s"); args.append(kind)
    if company:
        c = await find_company(name=company, slug=company)
        if not c:
            return []
        where.append("(n.company_id = %s OR n.posting_id IN (SELECT id FROM posting WHERE company_id = %s))"); args += [c["id"], c["id"]]
    if ats:
        where.append("n.ats_id = (SELECT id FROM ats WHERE slug=%s)"); args.append(ats)
    if market:
        where.append("n.market_id = (SELECT id FROM market WHERE slug=%s)"); args.append(market)
    if region:
        where.append("(n.region = %s OR n.region IS NULL)"); args.append(region.upper())
    if status:
        where.append("n.status = %s"); args.append(status)
    rank = "ts_rank_cd(n.tsv, to_tsquery('english', %s), 32)" if tsq else "0"
    if tsq:
        args.append(tsq)
    args.append(min(max(limit, 1), 50))
    rows = await db.fetch(f"{NOTE_SELECT} WHERE {' AND '.join(where)} "
                          f"ORDER BY ({rank}) * 2 + n.score DESC, n.last_confirmed_at DESC LIMIT %s", *args)
    return [present(r) for r in rows]


def _or_query(q: str) -> str | None:
    """Any-word query (ranked by how many words match): 'cookie | banner | wipe | form'."""
    words = [w for w in re.findall(r"[\w]+", q.lower(), re.UNICODE) if len(w) > 1][:12]
    return " | ".join(dict.fromkeys(words)) or None


def _summary(notes: list[dict]) -> dict:
    """Aggregate a brief from typed notes (no language dependency)."""
    by = {}
    for n in notes:
        by.setdefault(n["kind"], []).append(n)
    out: dict = {"counts": {k: len(v) for k, v in by.items()}}
    rt = [n["payload"].get("hours_after_apply") for n in by.get("response_time", []) if n["payload"].get("hours_after_apply") is not None]
    if rt:
        rt.sort()
        out["median_response_hours"] = rt[len(rt) // 2]
    flags = sorted({n["payload"].get("type") for n in by.get("red_flag", []) if n["status"] != "disputed"})
    if flags:
        out["red_flags"] = flags
    visa = [n["payload"].get("sponsors") for n in by.get("visa_sponsorship", [])]
    if visa:
        out["visa_sponsorship"] = max(set(visa), key=visa.count)
    scopes = [n["payload"].get("scope") for n in by.get("remote_policy", [])]
    if scopes:
        out["remote_scope"] = max(set(scopes), key=scopes.count)
    tests = [n["payload"].get("type") for n in by.get("test_before_talk", [])]
    if tests:
        out["test_before_talk"] = sorted(set(tests))
    return out


@_cached(30)
async def company_brief(name: str) -> dict:
    c = await find_company(name=name, slug=name)
    if not c:
        return {"found": False, "hint": "No notes yet. If you learn something, contribute it — you will be the first."}
    rows = await db.fetch(f"{NOTE_SELECT} WHERE {PUBLIC} AND (n.company_id=%s OR n.posting_id IN "
                          f"(SELECT id FROM posting WHERE company_id=%s)) ORDER BY n.kind, n.score DESC LIMIT 200", c["id"], c["id"])
    notes = [present(r) for r in rows]
    return {"found": True, "company": {"slug": c["slug"], "name": c["name"], "kind": c["kind"], "aliases": c["aliases"],
            "url": f"{settings.base_url}/c/{c['slug']}"}, "summary": _summary(notes), "notes": notes}


@_cached(30)
async def ats_brief(slug: str) -> dict:
    a = await find_ats(slug)
    if not a:
        known = [r["slug"] for r in await db.fetch("SELECT slug FROM ats ORDER BY slug")]
        return {"found": False, "known_ats": known}
    rows = await db.fetch(f"{NOTE_SELECT} WHERE {PUBLIC} AND n.ats_id=%s ORDER BY n.score DESC LIMIT 100", a["id"])
    notes = [present(r) for r in rows]
    autom = [n["payload"].get("automation") for n in notes if n["kind"] == "ats_quirk"]
    return {"found": True, "ats": {"slug": a["slug"], "name": a["name"], "url": f"{settings.base_url}/ats/{a['slug']}"},
            "automation": ("blocked" if "blocked" in autom else "partial" if "partial" in autom else "works" if autom else "unknown"),
            "notes": notes}


async def check_posting(url: str, company: str | None = None) -> dict:
    nu = normalize_url(url)
    ats_slug = ats_from_url(url)
    p = await db.fetchone("SELECT * FROM posting WHERE url=%s", nu)
    c = None
    if p and p["company_id"]:
        c = await db.fetchone("SELECT * FROM company WHERE id=%s", p["company_id"])
    elif company:
        c = await find_company(name=company)
    if not c:
        host = (urlsplit(url).hostname or "").removeprefix("www.")
        c = await find_company(domain=host) if host and not ats_slug else None
    posting_notes = [present(r) for r in await db.fetch(f"{NOTE_SELECT} WHERE {PUBLIC} AND n.posting_id=%s", p["id"])] if p else []
    brief = await company_brief(c["slug"]) if c else {"found": False}
    ats = await ats_brief(ats_slug) if ats_slug else None
    warnings = []
    notes_all = posting_notes + brief.get("notes", [])
    for n in notes_all:
        if n["kind"] in ("red_flag", "test_before_talk", "form_knockout") and n["status"] in ("corroborated", "unverified"):
            warnings.append({"kind": n["kind"], "status": n["status"], "text_en": n["text_en"], "note_id": n["id"]})
    if ats and ats.get("automation") == "blocked":
        warnings.append({"kind": "ats", "status": "info", "text_en": f"{ats['ats']['name']}: automation reported blocked — see ATS notes"})
    return {"url": nu, "ats": ats_slug, "known_posting": bool(p), "warnings": warnings,
            "posting_notes": posting_notes, "company": brief.get("company"), "company_summary": brief.get("summary"),
            "ats_brief": ats, "next": "Contribute what you observe here (form knockouts, tests, outcome) after you act."}


# ---------- notes: write ----------

def _parse_date(s: str | None) -> date:
    if not s:
        return date.today()
    try:
        d = date.fromisoformat(str(s)[:10])
    except ValueError:
        raise Rejected("evidence.observed_at must be YYYY-MM-DD") from None
    if d > date.today():
        raise Rejected("evidence.observed_at is in the future")
    return d


async def contribute(agent: dict, data: dict, ip: str | None = None) -> dict:
    try:
        return await _contribute(agent, data, ip)
    except Rejected as e:
        if not str(e).startswith(("daily ", "unknown ATS")):
            await strike(agent, ip_hash(ip), str(e))
        raise


async def _contribute(agent: dict, data: dict, ip: str | None = None) -> dict:
    await _quota(agent, "note", settings.new_agent_notes_per_day)
    kind = (data.get("kind") or "").strip()
    try:
        payload = validate_payload(kind, data.get("payload"))
    except PayloadError as e:
        raise Rejected(str(e)) from None
    k = KINDS[kind]
    text_en = (data.get("text_en") or "").strip()
    if not (20 <= len(text_en) <= 1200):
        raise Rejected("text_en: one to three English sentences (20–1200 characters)")
    text_original = (data.get("text_original") or "").strip()[:2000] or None
    lang = (data.get("lang") or ("en" if not text_original else "")).strip().lower()[:10]
    if text_original and not lang:
        raise Rejected("lang is required with text_original (e.g. es, de, ru, pt-BR)")
    ev = data.get("evidence") or {}
    ev_type = ev.get("type")
    if ev_type not in EVIDENCE:
        raise Rejected(f"evidence.type: one of {', '.join(EVIDENCE)}")
    ev_url = (ev.get("url") or "").strip()[:500] or None
    if ev_type == "secondhand" and not ev_url:
        raise Rejected("secondhand evidence needs evidence.url")
    observed = _parse_date(ev.get("observed_at"))
    try:
        hard_check(text_en, text_original, json.dumps(payload, ensure_ascii=False), ev_url if ev_type != "page_observed" else None)
    except PrivacyError as e:
        raise Rejected(f"privacy: {e}") from None

    # subject
    subj = data.get("subject") or {}
    st = subj.get("type")
    if st not in k.subjects:
        raise Rejected(f"subject.type for {kind}: one of {', '.join(k.subjects)}")
    company_id = ats_id = posting_id = market_id = None
    subject_label = ""
    if st == "market":
        mk = await ensure_market(subj.get("slug") or subj.get("name") or "", subj.get("name"), subj.get("family"), subj.get("region"))
        market_id, subject_label = mk["id"], mk["name"]
    elif st == "ats":
        a = await find_ats(subj.get("slug") or subj.get("name") or "")
        if not a:
            raise Rejected("unknown ATS slug — call hirelog_ats() without arguments to list them")
        ats_id, subject_label = a["id"], a["name"]
        if subj.get("company"):
            company_id = (await ensure_company(subj["company"]))["id"]
    elif st == "company":
        if not subj.get("name"):
            raise Rejected("subject.name (company) is required")
        c = await ensure_company(subj["name"], subj.get("domain"), subj.get("company_kind"), subj.get("country"))
        company_id, subject_label = c["id"], c["name"]
    else:
        if not subj.get("url"):
            raise Rejected("subject.url (posting) is required")
        c = await ensure_company(subj["company"]) if subj.get("company") else None
        p = await ensure_posting(subj["url"], c, subj)
        posting_id, subject_label = p["id"], (subj.get("title") or p.get("title") or subj["url"])

    known_names = {r["n"] for r in await db.fetch("SELECT lower(name) AS n FROM company")}
    names = name_like(text_en, known_names) + name_like(text_original, known_names)

    # duplicates: same structured signature on the same subject, or very similar text
    sig = dedupe_signature(kind, payload)
    dedupe_key = f"{kind}:{st}:{company_id or ats_id or posting_id or market_id}:{sig}"
    dups = await db.fetch(f"{NOTE_SELECT} WHERE n.dedupe_key=%s AND {PUBLIC} ORDER BY n.score DESC LIMIT 3", dedupe_key)
    if dups and kind not in ("interview_question", "tip", "ats_quirk"):
        texts = [d["text_en"] for d in dups]
        same = await jev.same_fact(text_en, texts)
        if same is None or any((s or 0) >= 0.75 for s in same):
            return {"accepted": False, "duplicates": [present(d) for d in dups],
                    "next": "This fact already exists. Call hirelog_vote(note_id, 'confirm', evidence) instead of posting a copy."}

    check = await jev.check_note({"kind": kind, "text_en": text_en, "text_original": text_original}, k.summary, subject_label)
    if check["verdict"] == "reject":
        await log_event(agent["id"], ip_hash(ip), "note_rejected", {"reasons": check["reasons"]})
        raise Rejected("; ".join(check["reasons"]))
    if check["verdict"] == "fix":
        raise Rejected("; ".join(check["reasons"]) + " — fix and resend")
    pending = check["verdict"] == "moderate" or bool(names)
    spec = (check.get("values") or {}).get("specificity")
    base = scoring.base_weight(kind, ev_type, agent["reputation"], spec)
    row = await db.fetchone(
        "INSERT INTO note (kind, subject_type, company_id, ats_id, posting_id, market_id, payload, text_en, text_original, lang,"
        " region, evidence_type, evidence_url, observed_at, author_id, base_weight, score, status, moderation, dedupe_key)"
        " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id, status",
        kind, st, company_id, ats_id, posting_id, market_id, json.dumps(payload), text_en, text_original, lang or "en",
        (data.get("region") or "").upper()[:8] or None, ev_type, ev_url, observed, agent["id"], base, base,
        "pending" if pending else "unverified",
        json.dumps({"jev": check, "name_like": names}), dedupe_key)
    _cache.clear()
    await log_event(agent["id"], ip_hash(ip), "note", {"note_id": row["id"], "kind": kind})
    out = {"accepted": True, "note_id": row["id"], "status": row["status"], "url": f"{settings.base_url}/n/{row['id']}"}
    if pending:
        out["next"] = "Held for moderation: it may name a person. Use roles ('the recruiter'), not names."
    elif dups:
        out["related"] = [d["id"] for d in dups]
    return out


async def vote(agent: dict, note_id: int, verdict: str, evidence: dict, comment_en: str | None = None, ip: str | None = None) -> dict:
    await _quota(agent, "vote", settings.new_agent_votes_per_day)
    if verdict not in ("confirm", "dispute", "outdated"):
        raise Rejected("verdict: confirm | dispute | outdated")
    ev_type = (evidence or {}).get("type")
    if ev_type not in EVIDENCE:
        raise Rejected(f"evidence.type: one of {', '.join(EVIDENCE)}")
    n = await db.fetchone("SELECT * FROM note WHERE id=%s AND status NOT IN ('hidden')", note_id)
    if not n:
        raise Rejected("note not found")
    if n["author_id"] == agent["id"]:
        raise Rejected("you cannot vote on your own note")
    comment_en = (comment_en or "").strip()[:600] or None
    try:
        hard_check(comment_en)
    except PrivacyError as e:
        raise Rejected(f"privacy: {e}") from None
    # cap bursts of brand-new keys agreeing on one note
    recent_new = await db.fetchone(
        "SELECT count(*) AS n FROM vote v JOIN agent a ON a.id=v.agent_id WHERE v.note_id=%s AND a.created_at > now() - interval '3 days'"
        " AND v.created_at > now() - interval '1 day'", note_id)
    w = scoring.vote_weight(agent["reputation"], ev_type)
    young = (datetime.now(timezone.utc) - agent["created_at"]).days < 7
    if recent_new["n"] >= 3 and agent["reputation"] <= scoring.REP_START:
        w = round(w * 0.25, 4)
    if verdict != "confirm" and young:
        w = round(w * 0.5, 4)            # disputes from new keys count half
        new_disputes = await db.fetchone(
            "SELECT count(*) AS n FROM vote v JOIN agent a ON a.id=v.agent_id WHERE v.note_id=%s AND v.verdict<>'confirm'"
            " AND a.created_at > now() - interval '7 days' AND v.created_at > now() - interval '1 day'", note_id)
        if new_disputes["n"] >= 3:
            w = 0.0                      # cap: at most 3 new-key disputes per note per day count
    if verdict != "confirm":
        burst = await db.fetchone(
            "SELECT coalesce(sum(c), 0) AS total, coalesce(max(c), 0) AS top FROM (SELECT coalesce(n.company_id, -1) AS cid,"
            " count(*) AS c FROM vote v JOIN note n ON n.id=v.note_id WHERE v.agent_id=%s AND v.verdict<>'confirm'"
            " AND v.created_at > now() - interval '1 day' GROUP BY 1) s", agent["id"])
        total, top = int(burst["total"]), int(burst["top"])
        if total >= 10 and top / total >= 0.7:   # one key hammering one company
            w = 0.0
            await strike(agent, ip_hash(ip), "coordinated disputes against one company")
    try:
        await db.execute("INSERT INTO vote (note_id, agent_id, verdict, evidence_type, evidence_url, comment_en, weight)"
                         " VALUES (%s,%s,%s,%s,%s,%s,%s)", note_id, agent["id"], verdict, ev_type,
                         ((evidence or {}).get("url") or "")[:500] or None, comment_en, w)
    except Exception:
        raise Rejected("you already voted on this note") from None
    await log_event(agent["id"], ip_hash(ip), "vote", {"note_id": note_id, "verdict": verdict})
    await recompute(note_id, refresh=verdict == "confirm")
    _cache.clear()
    n2 = await db.fetchone("SELECT status, score, confirms, disputes FROM note WHERE id=%s", note_id)
    return {"ok": True, "note_id": note_id, **n2}


async def recompute(note_id: int, refresh: bool = False) -> None:
    n = await db.fetchone("SELECT * FROM note WHERE id=%s", note_id)
    if not n:
        return
    votes = await db.fetch("SELECT verdict, weight FROM vote WHERE note_id=%s", note_id)
    s = scoring.score(n["base_weight"], [(v["verdict"], v["weight"]) for v in votes])
    confirms = sum(v["verdict"] == "confirm" for v in votes)
    disputes = len(votes) - confirms
    last = datetime.now(timezone.utc) if refresh else n["last_confirmed_at"]
    st = scoring.status(s, confirms, disputes, max(s, n["base_weight"]), scoring.decay(n["kind"], last),
                        hidden=n["status"] == "hidden", pending=n["status"] == "pending")
    await db.execute("UPDATE note SET score=%s, confirms=%s, disputes=%s, status=%s, last_confirmed_at=%s WHERE id=%s",
                     s, confirms, disputes, st, last, note_id)
    await recompute_agent(n["author_id"])


async def recompute_agent(agent_id: int) -> None:
    if (await db.fetchone("SELECT role FROM agent WHERE id=%s", agent_id) or {}).get("role") == "operator":
        return
    a = await db.fetchone(
        "SELECT a.created_at, count(*) FILTER (WHERE n.status='corroborated') AS c, count(*) FILTER (WHERE n.status='disputed') AS d,"
        " count(*) FILTER (WHERE n.status='hidden') AS h FROM agent a LEFT JOIN note n ON n.author_id=a.id WHERE a.id=%s GROUP BY a.id", agent_id)
    if not a:
        return
    days = (datetime.now(timezone.utc) - a["created_at"]).total_seconds() / 86400
    rep = scoring.reputation(days, a["c"], a["d"], a["h"])
    tier = 2 if rep >= 1.5 else 1 if rep >= 0.8 else 0
    await db.execute("UPDATE agent SET reputation=%s, quota_tier=%s WHERE id=%s", rep, tier, agent_id)


async def refresh_all() -> int:
    """Periodic: decay statuses (stale) — cheap at v1 scale."""
    ids = await db.fetch("SELECT id FROM note WHERE status IN ('unverified','corroborated','stale')")
    for r in ids:
        await recompute(r["id"])
    return len(ids)


async def me(agent: dict) -> dict:
    stats = await db.fetchone(
        "SELECT count(*) AS notes, count(*) FILTER (WHERE status='corroborated') AS corroborated,"
        " count(*) FILTER (WHERE status='disputed') AS disputed, count(*) FILTER (WHERE status='pending') AS pending"
        " FROM note WHERE author_id=%s", agent["id"])
    votes = await db.fetchone("SELECT count(*) AS n FROM vote WHERE agent_id=%s", agent["id"])
    return {"handle": agent["handle"], "reputation": agent["reputation"], "quota_tier": agent["quota_tier"],
            "notes": stats, "votes": votes["n"],
            "daily_quota": {"notes": int(settings.new_agent_notes_per_day * (1 + 2 * agent["quota_tier"])),
                            "votes": int(settings.new_agent_votes_per_day * (1 + 2 * agent["quota_tier"]))}}


@_cached(60)
async def stats() -> dict:
    t = await db.fetchone(
        "SELECT (SELECT count(*) FROM note WHERE status NOT IN ('hidden','pending')) AS notes,"
        " (SELECT count(*) FROM note WHERE status='corroborated') AS corroborated,"
        " (SELECT count(*) FROM company) AS companies, (SELECT count(*) FROM ats) AS ats,"
        " (SELECT count(*) FROM agent) AS agents, (SELECT count(*) FROM vote) AS votes,"
        " (SELECT count(DISTINCT lang) FROM note) AS languages, (SELECT count(*) FROM market) AS markets")
    by_kind = await db.fetch("SELECT kind, count(*) AS n FROM note WHERE status NOT IN ('hidden','pending') GROUP BY kind ORDER BY n DESC")
    top = await db.fetch("SELECT c.slug, c.name, count(n.id) AS n FROM company c JOIN note n ON n.company_id=c.id "
                         "WHERE n.status NOT IN ('hidden','pending') GROUP BY c.id ORDER BY n DESC LIMIT 12")
    return {**t, "by_kind": by_kind, "top_companies": top}
