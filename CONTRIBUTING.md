# Contributing to Hirelog

Thanks for helping. Hirelog is a small Python service (FastAPI + MCP SDK + Postgres). Most changes are easy to test because
validation, scoring and the privacy filter are pure functions.

## Dev setup

```bash
git clone https://github.com/tinyprocessing/hirelog && cd hirelog
uv venv --python 3.13 && source .venv/bin/activate
uv pip install -r requirements.txt pytest
python -m pytest -q tests          # unit tests, no database needed
```

To run the whole stack locally you need Postgres (the compose file ships pgvector/pgvector:pg17):

```bash
cp .env.example .env
docker compose up -d --build       # app on :8000 behind Caddy; API docs at /api/docs
```

Without Docker: start any Postgres 17 with the `pg_trgm` and `unaccent` extensions available, set `HIRELOG_DATABASE_URL`,
then `uvicorn app.main:app --reload`. Migrations in `app/migrations/*.sql` are applied automatically on start.

## Proposing a new note kind

Kinds are curated, not user-defined: typed facts are what make scoring, decay and search work.

1. Open an issue with the **New note kind** template first (fact captured, payload fields, half-life, dedupe signature, examples).
2. If accepted, one PR must contain all of:
   - a SQL migration in `app/migrations/` (next number, forward-only) if the schema, constraints or indexes change;
   - the `Kind(...)` entry in `app/kinds.py` (subjects, half-life, base weight, typed `fields` with enums) and its signature in `dedupe_signature`;
   - tests in `tests/` (valid and invalid payloads, dedupe);
   - the kind table in `README.md` and `docs/DESIGN.md`, and a mention in `app/playbook.py` (then regenerate `docs/PLAYBOOK.md`).
3. Prefer enums over free text. Payload values must be language-neutral; free text lives in `text_en` / `text_original`.
4. A kind describes **employer or hiring-system behaviour**, never a person.

## Code style

- Python 3.13, type hints, `from __future__ import annotations`, small functions, docstring on each module saying what it is for.
- Keep pure logic (`kinds.py`, `scoring.py`, `privacy.py`) free of I/O so it stays unit-testable.
- No new dependency without a reason in the PR; pin versions in `requirements.txt`.
- SQL: parameterised queries only, never string-built.
- Add or update a test for every behaviour change. CI runs `python -m pytest -q tests` on Python 3.13.

## Privacy rules for contributions

This project exists to share facts about employers, not people. In code, tests, seed data, docs, issues and screenshots:

- **No** names of recruiters, interviewers, candidates or employees; use roles ("the recruiter").
- **No** emails, phone numbers, personal profile links, meeting links, IBAN/ID-like numbers.
- **No** candidate data: nobody's own salary, CV text, immigration case or health. Pay bands are for a level at an employer.
- **No** live, confidential negotiation details that could identify someone.
- Seed data must be reviewed and describe closed processes or public facts only.
- Changes that weaken `app/privacy.py` or the moderation flow need a strong justification and extra tests.
- Never commit secrets (`.env`, API keys, admin tokens). Test fixtures use obviously fake values.

If you find personal data in the repo or the live service, follow [SECURITY.md](SECURITY.md) instead of opening a public issue.

## Pull requests

Small, focused PRs. Fill in the template, make sure tests pass, and explain the *why*. By contributing you agree your work is
released under the [MIT License](LICENSE) and that you follow the [Code of Conduct](CODE_OF_CONDUCT.md).
