from datetime import datetime, timedelta, timezone

import pytest

from app import scoring
from app.kinds import PayloadError, dedupe_signature, validate_payload
from app.privacy import PrivacyError, hard_check, name_like
from app.service import ats_from_url, normalize_url, slugify


def test_privacy_rejects_contacts():
    for t in ["write to kate@example.com", "call +34 675 69 41 02", "see linkedin.com/in/someone", "phone 675694102"]:
        with pytest.raises(PrivacyError):
            hard_check(t)


def test_privacy_allows_salary_and_dates():
    hard_check("Band €80 000–95 000 gross for senior, posted 2026-10-24, 3 rounds over 19 days.")
    hard_check("Rate £350/day inside IR35, 6 months, 2024 2025 2026.")


def test_name_like():
    assert name_like("The recruiter Kate Mazura asked about visa") == ["Kate Mazura"]
    assert name_like("Senior iOS at Scalable Capital in Greater London") == []
    assert name_like("Talent Acquisition said Monday") == []


def test_payload_validation():
    p = validate_payload("form_knockout", {"question": "Right to work?", "knockout_answer": "No", "effect": "Silent_Block", "junk": 1})
    assert p == {"question": "Right to work?", "knockout_answer": "No", "effect": "silent_block"}
    with pytest.raises(PayloadError):
        validate_payload("process", {"stages": ["recruiter", "magic"]})
    with pytest.raises(PayloadError):
        validate_payload("nope", {})
    assert dedupe_signature("process", {"stages": ["recruiter", "take_home"]}) == "recruiter,take_home"


def test_scoring_and_status():
    b = scoring.base_weight("form_knockout", "form_observed", 0.3, 3)
    s = scoring.score(b, [("confirm", 0.9), ("confirm", 0.7)])
    assert scoring.status(s, 2, 0, s, 1.0) in ("corroborated", "unverified")
    big = scoring.score(2.0, [("confirm", 1.0), ("confirm", 1.0)])
    assert scoring.status(big, 2, 0, big, 1.0) == "corroborated"
    neg = scoring.score(0.3, [("dispute", 1.0)])
    assert neg < 0 and scoring.status(neg, 0, 1, 0.3, 1.0) == "disputed"
    old = datetime.now(timezone.utc) - timedelta(days=180)
    assert scoring.decay("ats_quirk", old) < 0.26
    assert scoring.reputation(0, 0, 0, 0) == scoring.REP_START
    assert scoring.reputation(90, 10, 0, 0) == scoring.REP_MAX


def test_urls():
    assert normalize_url("https://www.linkedin.com/jobs/view/senior-ios-4483537261/?trackingId=x&refId=y") == "https://linkedin.com/jobs/view/4483537261"
    assert normalize_url("https://jobs.lever.co/acme/123/?utm_source=x&lever-source=y") == "https://jobs.lever.co/acme/123?lever-source=y"
    assert ats_from_url("https://acme.wd3.myworkdayjobs.com/en-US/careers/job/1") == "workday"
    assert ats_from_url("https://boards.greenhouse.io/acme/jobs/1") == "greenhouse"
    assert slugify("Scalable Capital GmbH") == "scalable-capital"


def test_name_like_sentence_starters():
    assert name_like("On Teamtailor career sites, click Decline first") == []
    assert name_like("Calling Workable's apply API in bulk") == []
    assert name_like("Asked by Colm Curran about pay") == ["Colm Curran"]


def test_is_english_gate():
    from app.service import is_english
    assert is_english("Workday candidate account before applying")
    assert not is_english("анкета молча блокирует отправку")
    assert not is_english("proceso de selección de REVEL")


def test_malformed_writes_are_not_strikes():
    from app.service import Invalid, Rejected
    assert issubclass(Invalid, Rejected)  # callers that catch Rejected still see it
