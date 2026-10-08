# Leaving: what you take with you

Offboarding is a first-class flow, not a hostage situation. Every layer has an export, and the removal purges bytes.

## What you can take out

| Layer | Export | Format | Goes where | Status |
| --- | --- | --- | --- | --- |
| Memory (events, facts) | `cortexdb export -o out.jsonl -S <scope> --include events --include facts` | JSONL, re-importable via `POST /v1/import` | any CortexDB, or your own tooling | tested |
| Memory (events, API) | `POST /v1/export {"scope": "<scope>", "format": "jsonl"}` | JSONL inline in the response | any CortexDB | tested; events only |
| Code index | `cortexdb code export-index <repo> out.bundle` (or `GET /v1/code/export-index?repo=<repo>`) | hash-verified bundle | another CortexDB server | tested |
| Code graph slice | `POST /v1/code/graph/query` with `"output"`: `json`, `graphml`, `neo4j_cypher`, `vis_html`, `d3_tree_html`, `svg`, `obsidian_vault`, `markdown_wiki` or `dot` | nine formats | GraphML to Gephi/Cytoscape, Cypher to Neo4j, DOT to Graphviz, HTML renders self-contained | tested (json, dot) |
| Team memory as a rules file | `cortexdb compose <brief> -S <scope>` | markdown with citation markers | paste into AGENTS.md / CLAUDE.md as a static handover | tested (needs `CORTEX_ANSWER_*` on the server) |

## Unplug the repository

```bash
curl -fsS -X DELETE http://<server>:3142/v1/code/repos/<name> \
  -H "Authorization: Bearer <key>" -H "X-Cortex-Actor: user:<name>"
```

The response reports `removed` and `purge.bytes_freed`: the index directory is deleted, the registry journal is rewritten without the checkout path. `503 REPO_PURGE_BUSY` means retry; the intent is already durable.

## Unwire the agent

Remove the `cortexdb` server from `.mcp.json`, and delete the CortexDB rules block from `CLAUDE.md` (it starts with `## CortexDB Codeplane`). The repository behaves exactly as before the pack ran; nothing in the checkout itself was modified beyond those two files.

## Erase everything

For a full teardown, `POST /v1/erasures` over the team scope purges every repository bound under it and reports the count; `POST /v1/forget` reaches code repositories under raw-event parity (`confirm_all: true`, empty selector, `layers: ["code"]`). Both are idempotent.

## Honest limits

- Index bundles import into CortexDB servers; the graph exports are the portable path to other tooling.
- `POST /v1/export` returns events, not derived records; the CLI `export --include facts` carries facts too.
- Exports are dumps, not backups: rebuild any time by re-registering the checkout.
