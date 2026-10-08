# 05 — Codeplane: give your coding agent code intelligence + team memory

> **Pack track:** `05-codeplane` in Onboarding-Packs — index a repository into CortexDB's Code Intelligence Plane and wire a coding agent (Claude Code first) to it, in one pass.

This track turns a repository checkout into something a coding agent can *see through*: cited snippets instead of grep sweeps, impact lists before edits, and the team's own reasons ("why is this code like this") inside the agent's context. It is the same CortexDB binary as the memory planes, started with the code plane on.

Who it is for: any team whose coding agent wastes turns rediscovering the same repository, every session. If your agent greps, you are paying for it.

## What's in this bundle

| File | What it is |
| --- | --- |
| `README.md` | This file. |
| `CODEPLANE-ONBOARDING.md` | The executable guide. Give it to a person or to the agent itself. |
| `rules-block.md` | The CLAUDE.md / AGENTS.md block that teaches the agent to prefer CortexDB tools. |
| `team-server.md` | One server for a team: scopes, actors, second and third repos. |
| `connectors.md` | GitHub history into team memory, so "why" questions have answers. |
| `exit.md` | Leaving: what you can take out, in which format, tested where. |
| `demo/` | The measurement harness: status line, A/B runner, and the `cortexdb-code` lifecycle CLI. |
| `env.example` | Environment variable template (placeholders only). |

## What you need

- Docker (or an existing CortexDB server with the code plane on).
- A repository checkout. Go, TypeScript/JavaScript, Python, C/C++, Java, Rust and more; tree-sitter extraction covers 43+ languages, no compiler needed for the default structural tier.
- No embedding key for the code plane. Structural retrieval (path, graph, BM25) needs nothing else; semantic code search is opt-in. Memory features want an embedding endpoint; see `team-server.md`.
- `cortexdb-mcp` 0.8.0 or newer on the agent machine (`pip install cortexdb-mcp`).

## One-liner (hand it to the agent)

In the repository root, with Claude Code running:

> Read `CODEPLANE-ONBOARDING.md` from `05-codeplane/` in the CortexDB Onboarding-Packs repo and run it on this repository. `PROJECT_DIR` = this repository. `CORTEXDB_URL` = `<your server, or omit to start one locally>`. `CORTEXDB_SCOPE` = `org:<org>/team:<team>`.

The deterministic alternative, no agent needed:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/cortex-db-ai/Onboarding-Packs/main/05-codeplane/demo/cortexdb-code) init
```

`init` starts a server if none is running (code plane on, port bound to localhost), registers the current checkout, wires Claude Code's `.mcp.json`, appends the rules block, and prints the index stats. `add <path>` grows to a second repo on the same server. `eject` exports everything and removes the repo.

## What you get once it's running

- `code_explore`: token-budgeted, cited evidence envelopes instead of grep. `files_considered`, `files_included`, `tokens_used`, and honest `uncertainty` on every answer.
- `code_impact`: reverse dependency closure with the weakest precision tier on each path. Callers and tests known *before* the diff.
- `code_inventory` / `code_graph`: bounded structure queries; deep traversals are refused, never silently truncated.
- `memory_search` / `memory_store`: the team's decisions, PR reasons and bugs, in the agent's context (needs the memory plane configured; `connectors.md` fills it from GitHub).
- Nothing leaves the machine you run the server on; the repo is mounted read-only and credential files are never indexed.

## Security

- The server binds to `127.0.0.1` by default. Do not expose it without setting `CORTEX_API_KEY` to a strong value.
- Repositories are mounted **read-only**. The plane indexes bytes; it never writes into your checkout.
- Do not commit `.env`, `.mcp.json` with real keys, or export files containing memory content.

## Honesty

- The code plane is single-node; there is no cluster mode.
- Compiler-grade answers (tier `Compiler`) need a SCIP index imported; the default tier is `Syntax`/`Manifest` and says so on every edge.
- The code plane's retrieval cues are English-only in v0.10.x even though the memory plane is multilingual.
- Index bundles import into another CortexDB; the graph exports (GraphML, DOT, Cypher, and more) go anywhere.
