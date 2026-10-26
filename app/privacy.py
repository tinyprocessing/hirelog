"""Server-side personal-data filter. Runs before anything is stored.

Hard rejects: contact details and personal profile links. Soft flags: things that look like a person's name
(sent to moderation instead of public). The Jev check (app.jev) adds a model opinion on top.
"""
from __future__ import annotations

import re

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE = re.compile(r"(?<![\w/])\+\d[\d ()\-.]{7,}\d|(?<![\w/.,])\d{9,15}(?![\w.,])")
PROFILE = re.compile(r"(linkedin\.com/in/|t\.me/|wa\.me/|instagram\.com/|facebook\.com/(?!careers)|x\.com/(?!\w+/status)|twitter\.com/)", re.I)
IBAN = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b")
# Two capitalised words with a person-ish first word, e.g. "Kate Mazura", "Colm Curran".
NAME_PAIR = re.compile(r"\b([A-Z][a-zà-ÿ]{1,14})\s+([A-Z][a-zà-ÿ'\-]{2,20})\b")
SAFE_FIRST = {"The", "This", "Senior", "Lead", "Staff", "Principal", "Head", "Talent", "Technical", "Hiring", "Engineering",
              "Mobile", "Product", "Google", "Apple", "Linked", "Easy", "Apply", "Swift", "Android", "Remote", "United", "New",
              "San", "Los", "Tel", "Hong", "Las", "Santa", "North", "South", "East", "West", "Great", "Greater", "Big",
              "Jetpack", "React", "Visual", "Xcode", "Kotlin", "Data", "Machine", "Solutions", "Sales", "Customer",
              "Forward", "Deployed", "Software", "Backend", "Frontend", "Full", "Platform", "Cloud", "Security", "Talent",
              "People", "Human", "Recruiting", "Recruitment", "Interview", "Round", "Stage", "First", "Second", "Third",
              "Final", "Take", "Home", "Live", "Coding", "System", "Design", "Values", "Blue", "Card", "Skilled", "Worker",
              "Scalable", "Nord", "Security", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
              "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"}


class PrivacyError(ValueError):
    pass


def hard_check(*texts: str | None) -> None:
    for t in texts:
        if not t:
            continue
        if EMAIL.search(t):
            raise PrivacyError("contains an email address — remove contact details")
        if PROFILE.search(t):
            raise PrivacyError("contains a personal profile link — use roles, not people")
        if IBAN.search(t):
            raise PrivacyError("contains an account/ID-like number")
        for m in PHONE.finditer(t):
            if 9 <= len(re.sub(r"\D", "", m.group(0))) <= 15:
                raise PrivacyError("contains a phone number — remove contact details")


def name_like(text: str | None, known: set[str] = frozenset()) -> list[str]:
    """Candidate person names, excluding known company/product words."""
    if not text:
        return []
    out = []
    for m in NAME_PAIR.finditer(text):
        a, b = m.group(1), m.group(2)
        if a in SAFE_FIRST or b in SAFE_FIRST or f"{a} {b}".lower() in known:
            continue
        out.append(f"{a} {b}")
    return out
