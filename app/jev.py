"""Write-time checks with Jev (TypeSafe System One): cheap typed questions, never a single point of failure.

Answers: noul → {"noul": p}, choice → {"choice": key, "confidence": c}, score → {"score": level}.
Mode (HIRELOG_JEV_MODE): off | shadow (log only) | on (act on thresholds).
"""
from __future__ import annotations

import logging
import time

import httpx

from .config import settings

log = logging.getLogger("hirelog.jev")
URL = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-latest"

NOTE_QUESTIONS = {
    "names_private_person": {"type": "noul", "instructions":
        "Does `text_en` or `text_original` name or identify a private individual (a recruiter, interviewer, candidate or "
        "employee by name, initials with surname, or a unique personal detail)? Company names, product names and public "
        "brands are not private individuals."},
    "about_candidate": {"type": "noul", "instructions":
        "Is the text mainly about the job seeker's own private data (their own salary, CV, health, family, location, "
        "immigration case) rather than about how an employer, job posting or hiring software behaves?"},
    "kind_fits": {"type": "noul", "instructions":
        "Does the text actually describe a fact of type `kind` (see `kind_summary`) about `subject`?"},
    "promo_or_spam": {"type": "noul", "instructions":
        "Is the text advertising, a recruiting pitch, self-promotion, or unrelated to hiring?"},
    "specificity": {"type": "score", "instructions":
        "How concrete and observed is the statement?", "criteria": [
            "a vague opinion or feeling with no observable detail",
            "a general claim with one detail",
            "a concrete observation of what happened or what a page/form/email showed",
            "a concrete observation with numbers, stages, wording or timing"]},
}
TRANSLATION_Q = {"faithful_translation": {"type": "noul", "instructions":
    "Do `text_en` and `text_original` state the same facts (same numbers, same meaning), even if worded differently?"}}
SAME_FACT_Q = {"type": "noul", "instructions":
    "Do `a` and `b` state the same fact about the same subject (they would be confirmed or refuted by the same evidence)?"}


async def ask(state: dict, questions: dict, timeout: float = 4.0) -> dict | None:
    if settings.jev_mode == "off" or not settings.typesafe_api_key:
        return None
    t0 = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=timeout) as c:
            r = await c.post(URL, json={"model": MODEL, "state": state, "questions": questions},
                             headers={"Authorization": f"Bearer {settings.typesafe_api_key}"})
        r.raise_for_status()
        data = r.json()
    except Exception as e:  # noqa: BLE001 — the checker is advisory
        log.warning("jev unavailable after %.1fs: %r", time.monotonic() - t0, e)
        return None
    log.info("jev %d questions in %.1fs, %s input tokens", len(questions), time.monotonic() - t0,
             (data.get("usage") or {}).get("input_tokens"))
    return data.get("answers") or {}


def _noul(answers: dict, key: str) -> float | None:
    try:
        return round(float(answers[key]["noul"]), 3)
    except (KeyError, TypeError, ValueError):
        return None


async def check_note(note: dict, kind_summary: str, subject: str) -> dict:
    """Returns {"values": {...}, "verdict": "ok"|"moderate"|"reject"|"fix", "reasons": [...]}"""
    state = {"kind": note["kind"], "kind_summary": kind_summary, "subject": subject,
             "text_en": note["text_en"], "text_original": note.get("text_original") or ""}
    qs = dict(NOTE_QUESTIONS)
    if note.get("text_original"):
        qs.update(TRANSLATION_Q)
    answers = await ask(state, qs)
    if answers is None:
        return {"values": None, "verdict": "ok", "reasons": ["checker_unavailable"]}
    v = {k: _noul(answers, k) for k in qs if qs[k]["type"] == "noul"}
    try:
        v["specificity"] = int(answers["specificity"]["score"])
    except (KeyError, TypeError, ValueError):
        v["specificity"] = None
    reasons, verdict = [], "ok"
    if (v.get("about_candidate") or 0) >= 0.5:
        verdict, reasons = "reject", ["about the job seeker's own data, not the employer"]
    elif (v.get("promo_or_spam") or 0) >= 0.5:
        verdict, reasons = "reject", ["looks like promotion or unrelated content"]
    elif note.get("text_original") and (v.get("faithful_translation") or 1) < 0.6:
        verdict, reasons = "fix", ["text_en does not say the same as text_original"]
    elif (v.get("names_private_person") or 0) >= 0.5:
        verdict, reasons = "moderate", ["may name a private person"]
    elif (v.get("kind_fits") or 1) < 0.4:
        verdict, reasons = "fix", [f"text does not look like a '{note['kind']}' fact"]
    if settings.jev_mode == "shadow":
        return {"values": v, "verdict": "ok", "shadow_verdict": verdict, "reasons": reasons}
    return {"values": v, "verdict": verdict, "reasons": reasons}


async def same_fact(a: str, b_list: list[str]) -> list[float | None] | None:
    if not b_list:
        return []
    state = {"a": a, **{f"b{i}": b for i, b in enumerate(b_list)}}
    qs = {f"s{i}": {**SAME_FACT_Q, "instructions": SAME_FACT_Q["instructions"].replace("`b`", f"`b{i}`")}
          for i in range(len(b_list))}
    answers = await ask(state, qs)
    if answers is None:
        return None
    return [_noul(answers, f"s{i}") for i in range(len(b_list))]
