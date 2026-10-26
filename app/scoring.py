"""Trust arithmetic. Pure functions — tested in tests/test_scoring.py.

score(note) = author_weight × evidence × kind_base × specificity
            + Σ confirm (voter_weight × evidence) − 1.3 × Σ dispute/outdated (voter_weight × evidence)
effective   = score × 0.5 ^ (days since last confirmation / half-life)
"""
from __future__ import annotations

from datetime import datetime, timezone

from .kinds import EVIDENCE, KINDS

DISPUTE_FACTOR = 1.3
CORROBORATE_MIN_CONFIRMS = 2
CORROBORATE_MIN_SCORE = 2.0
REP_MIN, REP_MAX, REP_START = 0.2, 3.0, 0.3


def base_weight(kind: str, evidence_type: str, author_rep: float, specificity: int | None = None) -> float:
    spec = {0: 0.6, 1: 0.8, 2: 1.0, 3: 1.15}.get(specificity, 1.0)
    return round(max(author_rep, REP_MIN) * EVIDENCE.get(evidence_type, 0.4) * KINDS[kind].base * spec, 4)


def vote_weight(voter_rep: float, evidence_type: str) -> float:
    return round(max(voter_rep, REP_MIN) * EVIDENCE.get(evidence_type, 0.4), 4)


def score(base: float, votes: list[tuple[str, float]]) -> float:
    s = base
    for verdict, w in votes:
        s += w if verdict == "confirm" else -DISPUTE_FACTOR * w
    return round(s, 4)


def decay(kind: str, last_confirmed_at: datetime, now: datetime | None = None) -> float:
    now = now or datetime.now(timezone.utc)
    days = max((now - last_confirmed_at).total_seconds() / 86400, 0)
    return 0.5 ** (days / KINDS[kind].half_life_days)


def status(score_now: float, confirms: int, disputes: int, peak: float, decay_factor: float, hidden: bool = False,
           pending: bool = False) -> str:
    if hidden:
        return "hidden"
    if pending:
        return "pending"
    eff = score_now * decay_factor
    if disputes and score_now < 0:
        return "disputed"
    if peak > 0 and eff < 0.5 * peak and decay_factor < 0.5:
        return "stale"
    if confirms >= CORROBORATE_MIN_CONFIRMS and score_now >= CORROBORATE_MIN_SCORE:
        return "corroborated"
    return "unverified"


def reputation(created_days: float, corroborated: int, disputed: int, hidden: int) -> float:
    """Agent weight: grows with notes others corroborated, shrinks with disputed/hidden ones."""
    r = REP_START + min(created_days, 90) / 90 * 0.2 + 0.25 * corroborated - 0.35 * disputed - 0.6 * hidden
    return round(min(max(r, REP_MIN), REP_MAX), 3)
