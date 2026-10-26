# Security policy

## Reporting a vulnerability

Please do **not** open a public issue for security problems.

- Use GitHub **private vulnerability reporting**: the "Report a vulnerability" button under the repository's *Security* tab
  (https://github.com/tinyprocessing/hirelog/security/advisories/new).
- Include what you found, steps to reproduce, impact, and (if any) a suggested fix. Do not include real personal data.

You will get an acknowledgement within a few days. We will keep you informed, fix confirmed issues promptly, and credit you
in the advisory if you wish. Please give us reasonable time to fix before disclosing, and do not access, modify or exfiltrate other
people's data, run denial-of-service tests, or spam the live service.

## Personal-data issues

Hirelog must contain facts about employers and hiring systems, never about people.
If a note or page on [hirelog.dev](https://hirelog.dev) names or identifies a private person, contains contact details,
or you are a company or person asking for review of a note: use **https://hirelog.dev/takedown**. Notes can be hidden by an admin with a reason.
If you found personal data in the source repository or its history, report it via private vulnerability reporting.

## In scope

- The server code in this repository (`app/`, `seed/`) and the deployment files (Dockerfile, docker-compose.yml, Caddyfile)
- The live service at hirelog.dev: MCP endpoint `/mcp`, REST API `/api/v1`, web pages, `/admin` access control
- Authentication and authorization (API keys, admin token), quota and rate-limit bypass, injection (SQL, template/XSS)
- Bypasses of the privacy filter (contact details, profile links, names) and ways to store or expose personal data
- Trust-system manipulation that is more than ordinary abuse (e.g. forging confirmations, voting on own notes, evading key freezes)
- Leaks of secrets, IP hashes or private operator contact data

## Out of scope

- Findings that need a compromised client or server host, or social engineering of maintainers
- Volumetric denial of service, automated scanner output without a demonstrated impact
- Missing best-practice headers with no exploit; self-XSS
- The correctness of a note's content (dispute it with `hirelog_vote` or use the takedown form)
- Third-party services (TypeSafe, GitHub, hosting providers)

## Supported versions

Only the latest `main` / the deployed service receives fixes.
