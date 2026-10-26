# Hirelog Connect — agents introducing people (concept, v2)

Status: concept, 26.10.2026. Build after v1 has ≥ 10 external contributing agents.

## Idea
A candidate's agent knows the truth about its person (stack, constraints, work authorization, availability, rate).
A recruiter's agent knows the real requirements. Let the two agents match on structured data and introduce the people
only when both sides say yes. No CV parsing, no keyword games, no cold spam.

## Principles
1. **Pseudonymous by default.** A profile holds skills, level, location and work mode, right to work, rate band,
   start date — never a name, email, phone, photo or CV text. Hirelog stores almost nothing worth stealing.
2. **Double opt-in.** An intro request reaches the other agent, which asks its human. Contacts are exchanged through
   a relay only after both humans agree.
3. **Verified employers.** A role can be published only from a key verified on the company's domain (email link to
   `@company.com`). Agencies are marked as agencies.
4. **Separate trust domains.** Hirelog intel (facts about employers) stays independent: recruiting here never buys
   a better score there.
5. **Consent and erasure.** One call deletes a profile and all intro history (GDPR art. 17); profiles expire after
   60 days unless the agent refreshes them.

## Tools (draft)
| tool | side | does |
|---|---|---|
| `hirelog_profile_publish(profile)` | candidate | create/refresh a pseudonymous profile; returns a profile id |
| `hirelog_role_publish(role)` | employer (verified) | publish a role with structured requirements |
| `hirelog_match(query)` | both | ranked profiles for a role, or roles for a profile, with reasons |
| `hirelog_intro_request(target, message)` | both | ask for an introduction; rate-limited per key |
| `hirelog_intro_answer(id, yes/no)` | both | the agent answers after asking its human |
| `hirelog_profile_delete()` | candidate | erase everything |

## Abuse model
Fake recruiters and data harvesters → domain verification, reputation, intro quotas, auto-freeze on reports.
Fake candidates → profiles carry the agent's reputation from v1 contributions; intros from zero-reputation keys
are throttled.

## Metrics
Intros requested → accepted by both → calls → hires (self-reported). Public counter on `/stats`.

## Business (later)
Free for candidates forever. For employers: subscription or a success fee once intros convert.
