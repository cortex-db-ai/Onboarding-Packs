# 03 — Attach chat / IDE / Grok to an existing brain

Point Claude Code, Claude Desktop, Cursor, or Grok Bot at a **working** CortexDB identity (shared Personal-Brain preferred). No new product UI — harness packs only.

## Packs

| Folder | Harness | Entry |
|---|---|---|
| **`Grokbot/`** | Grok Bot (HTTP helper) | `GROKBOT-ONBOARDING.md` |
| **`ClaudeCode/`** | Claude Code MCP | `CLAUDE-CODE-ONBOARDING.md` |
| **`ClaudeDesktop/`** | Claude Desktop MCP | `CLAUDE-DESKTOP-ONBOARDING.md` |
| **`Cursor/`** | Cursor MCP + rules | `CURSOR-ONBOARDING.md` |

## Claude Code vs Claude Desktop

| | Claude Code | Claude Desktop |
|---|---|---|
| Config | **`~/.claude.json`** → `mcpServers` (not `~/.claude/mcp.json`) | **`~/Library/Application Support/Claude/claude_desktop_config.json`** |
| Recommended command | `/opt/homebrew/bin/python3` + `-m cortexdb_mcp` (or script / traced wrapper OK) | **Direct** `/opt/homebrew/bin/cortexdb-mcp`, `args: []` — traced wrappers have wedged Desktop |
| Label | `harness:claude-code` | `harness:claude-desktop` |
| Reload | Restart Claude Code | **Cmd+Q**, reopen, **new chat**, enable cortexdb connector |

## Audience

- **Vibe coders** and **agent operators** who already have a brain and want recall/write in the tools they live in.
- Prefer shared brain; never mint over a working token.

For app dual-write into a product repo, use `02-app-in-repo/` instead.

To sanity-check a harness's brain after wiring it, use the smoke patterns in
[`../examples/`](../examples/) — one store + one recall with the harness's own `.env`.
