## What and why

<!-- One or two sentences. Link the issue if there is one. -->

## Checklist

- [ ] `python -m pytest -q tests` passes
- [ ] New behaviour has a test (validators, scoring and privacy filter are pure functions - easy to test)
- [ ] No personal data in code, tests, seed data or screenshots (names, emails, phones, profile links, candidate data)
- [ ] If this touches note kinds: migration + `app/kinds.py` + `docs/DESIGN.md` updated together
- [ ] If this changes the playbook: `docs/PLAYBOOK.md` regenerated from `app/playbook.py`
- [ ] No secrets committed (`.env` stays local)
