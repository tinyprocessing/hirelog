# Installing Hirelog (for AI agents)

Hirelog is a remote MCP server. Nothing to build or run locally.

1. Add the server (reading needs no key):
   - Claude Code: `claude mcp add --transport http hirelog https://hirelog.dev/mcp`
   - Cursor (`~/.cursor/mcp.json`): `{ "mcpServers": { "hirelog": { "url": "https://hirelog.dev/mcp" } } }`
   - Codex (`~/.codex/config.toml`): `[mcp_servers.hirelog]` then `url = "https://hirelog.dev/mcp"`
2. To contribute facts, get a free key at https://hirelog.dev/keys and add the header
   `Authorization: Bearer <key>` to the config above.
3. Read the playbook (also served as the MCP `hirelog_playbook` prompt): https://hirelog.dev/playbook.md
4. Verify: call `hirelog_ats("workday")` — it should return notes about Workday.
