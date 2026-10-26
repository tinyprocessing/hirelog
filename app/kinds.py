"""Note kinds: what can be said, about what, and how long it stays true.

Payload validation is deliberately small: known keys, enum values, types. Unknown keys are dropped,
so agents can be generous without polluting the store.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

STAGES = ["recruiter", "hiring_manager", "take_home", "live_coding", "system_design", "technical_talk",
          "values", "panel", "trial_days", "presentation", "reference_check", "offer"]
TOPICS = ["swift_concurrency", "swiftui", "uikit", "memory", "architecture", "testing", "performance",
          "mobile_system_design", "android_kotlin", "kmp", "react_native", "backend", "system_design",
          "llm_system_design", "rag", "evals", "agents", "coding_algorithms", "behavioural", "leadership",
          "product", "right_to_work", "salary", "motivation", "other"]


@dataclass(frozen=True)
class Field:
    type: str                      # str | int | float | bool | enum | list_enum | list_str
    enum: tuple[str, ...] = ()
    required: bool = False


@dataclass(frozen=True)
class Kind:
    name: str
    subjects: tuple[str, ...]
    half_life_days: int
    base: float                    # intrinsic weight of this kind (tip is lowest)
    fields: dict[str, Field] = field(default_factory=dict)
    summary: str = ""


def _e(*v: str) -> tuple[str, ...]:
    return tuple(v)


KINDS: dict[str, Kind] = {k.name: k for k in [
    Kind("process", ("company",), 365, 1.0, {
        "stages": Field("list_enum", tuple(STAGES), True),
        "rounds": Field("int"), "duration_days": Field("int"),
        "role_family": Field("str"),
    }, "Hiring stages in order, rounds and total duration."),
    Kind("interview_question", ("company",), 540, 1.0, {
        "stage": Field("enum", tuple(STAGES), True),
        "topic": Field("enum", tuple(TOPICS), True),
        "question_en": Field("str", required=True),
        "role_family": Field("str"),
    }, "A question that was actually asked, at which stage."),
    Kind("test_before_talk", ("company", "posting"), 180, 1.0, {
        "type": Field("enum", _e("hackerrank", "codility", "testgorilla", "take_home", "personality", "cognitive", "video_interview", "other"), True),
        "before_human_contact": Field("bool", required=True),
    }, "An assessment sent before any human conversation."),
    Kind("form_knockout", ("posting", "company"), 120, 1.0, {
        "question": Field("str", required=True),
        "knockout_answer": Field("str", required=True),
        "effect": Field("enum", _e("silent_block", "instant_reject", "auto_reject_later", "warning_shown"), True),
    }, "A form question whose answer silently blocks or rejects."),
    Kind("ats_quirk", ("ats",), 90, 1.0, {
        "symptom": Field("str", required=True),
        "workaround": Field("str"),
        "automation": Field("enum", _e("works", "partial", "blocked"), True),
        "area": Field("enum", _e("account", "file_upload", "phone", "address", "cookie_banner", "dropdown", "captcha", "submit", "autofill", "other")),
    }, "How an ATS behaves for an agent filling it, and what works."),
    Kind("response_time", ("company",), 180, 1.0, {
        "event": Field("enum", _e("auto_reject", "human_reject", "human_reply", "screen_invite", "interview_invite", "offer", "ghosted"), True),
        "hours_after_apply": Field("float"),
        "channel": Field("enum", _e("email", "ats_portal", "linkedin", "phone", "other")),
    }, "How long after applying something happened."),
    Kind("outcome_pattern", ("company", "posting"), 270, 1.0, {
        "pattern": Field("enum", _e("rejects_outside_location", "needs_local_language", "needs_local_work_permit", "sponsors_visa",
                                     "b2b_ok", "contractors_only", "senior_only", "reposts_same_role", "hires_through_agency",
                                     "fast_rejects_without_review", "other"), True),
        "segment": Field("str"),
    }, "A repeated employer behaviour visible across candidates."),
    Kind("remote_policy", ("company", "posting"), 270, 1.0, {
        "scope": Field("enum", _e("onsite", "country", "eu", "emea", "europe_tz", "americas", "worldwide"), True),
        "via": Field("enum", _e("employee", "eor", "contractor", "any")),
        "office_days": Field("float"), "countries": Field("list_str"),
    }, "Where people can actually work from, and how they are hired."),
    Kind("visa_sponsorship", ("company", "posting"), 270, 1.0, {
        "sponsors": Field("enum", _e("yes", "no", "case_by_case"), True),
        "countries": Field("list_str"), "program": Field("str"),
    }, "Whether the employer sponsors work permits, for which country."),
    Kind("salary_band", ("company", "posting"), 365, 1.0, {
        "min": Field("int", required=True), "max": Field("int"),
        "currency": Field("str", required=True),
        "period": Field("enum", _e("year", "month", "day", "hour"), True),
        "level": Field("str"), "country": Field("str"),
        "source": Field("enum", _e("posted", "recruiter_said", "offer"), True),
        "gross": Field("bool"),
    }, "A pay range for a level — never the person's own pay."),
    Kind("red_flag", ("company", "posting"), 365, 1.1, {
        "type": Field("enum", _e("lead_farm", "fake_company", "pay_to_apply", "data_harvest", "ghost_job", "mlm",
                                 "aggregator_repost", "bait_and_switch", "other"), True),
    }, "Something that wastes or endangers the candidate."),
    Kind("tip", ("company", "ats", "posting"), 180, 0.6, {}, "Use only when no other kind fits."),
]}

EVIDENCE = {"email_received": 1.0, "call_happened": 1.0, "form_observed": 0.9, "page_observed": 0.7, "secondhand": 0.4}


class PayloadError(ValueError):
    pass


def _coerce(name: str, f: Field, v: Any) -> Any:
    if f.type == "str":
        if not isinstance(v, str):
            raise PayloadError(f"{name}: expected text")
        return v.strip()[:600]
    if f.type == "int":
        try:
            return int(v)
        except (TypeError, ValueError):
            raise PayloadError(f"{name}: expected integer") from None
    if f.type == "float":
        try:
            return float(v)
        except (TypeError, ValueError):
            raise PayloadError(f"{name}: expected number") from None
    if f.type == "bool":
        if isinstance(v, bool):
            return v
        raise PayloadError(f"{name}: expected true/false")
    if f.type == "enum":
        v = str(v).strip().lower()
        if v not in f.enum:
            raise PayloadError(f"{name}: one of {', '.join(f.enum)}")
        return v
    if f.type == "list_enum":
        if not isinstance(v, list) or not v:
            raise PayloadError(f"{name}: non-empty list")
        out = [str(x).strip().lower() for x in v]
        bad = [x for x in out if x not in f.enum]
        if bad:
            raise PayloadError(f"{name}: unknown {bad}; allowed {', '.join(f.enum)}")
        return out[:20]
    if f.type == "list_str":
        if not isinstance(v, list):
            raise PayloadError(f"{name}: list of text")
        return [str(x).strip()[:80] for x in v][:30]
    raise PayloadError(f"{name}: unsupported")


def validate_payload(kind: str, payload: dict | None) -> dict:
    k = KINDS.get(kind)
    if not k:
        raise PayloadError(f"unknown kind '{kind}'; one of {', '.join(KINDS)}")
    payload = payload or {}
    if not isinstance(payload, dict):
        raise PayloadError("payload must be an object")
    out = {}
    for name, f in k.fields.items():
        if name in payload and payload[name] not in (None, ""):
            out[name] = _coerce(name, f, payload[name])
        elif f.required:
            raise PayloadError(f"payload.{name} is required for {kind}")
    return out


def dedupe_signature(kind: str, payload: dict) -> str:
    """Kind-specific fields that define 'the same fact'."""
    keys = {"process": ("stages",), "interview_question": ("stage", "topic"), "test_before_talk": ("type",),
            "form_knockout": ("effect",), "ats_quirk": ("area", "automation"), "response_time": ("event",),
            "outcome_pattern": ("pattern",), "remote_policy": ("scope", "via"), "visa_sponsorship": ("sponsors",),
            "salary_band": ("currency", "period", "level"), "red_flag": ("type",), "tip": ()}[kind]
    parts = []
    for key in keys:
        v = payload.get(key)
        parts.append(",".join(v) if isinstance(v, list) else str(v or ""))
    return "|".join(parts)


def schema_doc() -> list[dict]:
    """Machine-readable kind catalogue, served to agents."""
    return [{"kind": k.name, "subjects": list(k.subjects), "summary": k.summary, "half_life_days": k.half_life_days,
             "fields": {n: {"type": f.type, "required": f.required, **({"values": list(f.enum)} if f.enum else {})}
                        for n, f in k.fields.items()}} for k in KINDS.values()]
