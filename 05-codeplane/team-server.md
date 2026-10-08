# One server for the team

The code plane is single-node, and that is enough for a team: one keyed self-hosted server, repositories bound to team scopes, every developer's agent pointed at the same URL. A decision stored by one developer's agent is found by the next one's.

## Layout

| Piece | Value |
| --- | --- |
| Server | one `cortexdb/cortexdb:v0.10.5` container, code plane on, port bound to the team's network |
| Repos | mounted read-only under `/repos`, each registered with `POST /v1/code/repos` |
| Scopes | one team scope per project: `org:<org>/team:<team>`; the server binds each repo under `<scope>/repo:<name>-<12 hex>` |
| Actors | one per developer: `user:<name>` via the `X-Cortex-Actor` header |
| Keys | `CORTEX_API_KEY` on the server; the same value as `CORTEXDB_API_KEY` in each agent's MCP env |

## Bring up

```bash
docker run -d --name cortexdb-team \
  -p 127.0.0.1:3142:3141 \
  -e CORTEX_CODE_PLANE=1 -e CORTEX_CODE_WATCH=1 -e CORTEX_CODE_BUNDLE=1 \
  -e CORTEX_CODE_REPO_ROOTS=/repos \
  -e CORTEX_API_KEY=<team-key> \
  -v cortexdb_team_data:/data \
  -v /srv/repos:/repos:ro \
  cortexdb/cortexdb:v0.10.5
```

For memory features, add the embedding environment (`CORTEX_EMBEDDING_PROVIDER` / `_URL` / `_MODEL` / `_DIMS` / `_API_KEY`, and optionally `CORTEX_ANSWER_*`, `CORTEX_ENRICHMENT_*`). Everything local is supported: `provider=ollama` with a local endpoint keeps embeddings on your GPUs. The code plane itself never needs any of this.

## Seat the team

Each developer's `.mcp.json` (Claude Code) or equivalent MCP config:

```json
{
  "mcpServers": {
    "cortexdb": {
      "type": "stdio",
      "command": "cortexdb-mcp",
      "env": {
        "CORTEXDB_URL": "http://<team-server>:3142",
        "CORTEXDB_API_KEY": "<team-key>",
        "CORTEXDB_ACTOR": "user:<name>",
        "CORTEXDB_SCOPE": "org:<org>/team:<team>"
      }
    }
  }
}
```

Verify per seat:

```bash
curl -fsS -H "Authorization: Bearer <team-key>" -H "X-Cortex-Actor: user:<name>" \
  http://<team-server>:3142/v1/code/repos
```

## Add a repository

```bash
curl -fsS -X POST http://<team-server>:3142/v1/code/repos \
  -H "Authorization: Bearer <team-key>" -H "X-Cortex-Actor: user:<name>" \
  -H "Content-Type: application/json" \
  -d '{"name":"<repo>","path":"/repos/<repo>","scope":"org:<org>/team:<team>"}'
```

Second repo, third repo: same server, same scope. `code_explore` accepts `repos` to answer across all of them in one budgeted call; each item is cited per repo. Each new checkout (worktree) registers as its own repo entry.

## Governance notes

- A registration is a create, not a rebind: `409 REPO_EXISTS` means remove first (`DELETE /v1/code/repos/<name>` frees its bytes) or use a new name.
- With per-actor verified tokens, a repository under an ungoverned scope answers `404 REPO_NOT_FOUND` until the scope is registered and members seated (`POST /v1/scopes`, `PUT /v1/scopes/members`). Operator keys bypass rosters; use them for bootstrap, not for people.
- The server warns at startup if `CORTEX_CODE_REPO_ROOTS` is unset; set it.
- Single-node is the only supported topology; plan capacity as one node per team or repo group, on the order of millions of events plus the index.
