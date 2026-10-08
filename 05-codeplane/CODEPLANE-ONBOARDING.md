# CortexDB Codeplane onboarding (execute this)

You are an agent (Claude Code itself, or another agent with shell and file access). The user gave you this pack because they want CortexDB's code plane serving this repository, wired into your tools, in one pass. Execute every numbered section in order. Run every verification step. Do not print tokens or API keys. Do not commit secrets.

`PACK` = the folder that contains this file.

Goal: by the end, `code_explore` answers a question about this repository with cited snippets, `code_impact` lists callers of a symbol, and the user's CLAUDE.md tells every future session to use them first.

## 0. Inputs

- `PROJECT_DIR` = the repository to index (default: the directory you are running in).
- `CORTEXDB_URL` = an existing server with the code plane on, or empty to start one locally.
- `CORTEXDB_API_KEY` = the server's key (default `codeplane-local-key` for a local one; set a strong value if the port is reachable by anyone else).
- `CORTEXDB_ACTOR` = your actor id (default `user:dev`).
- `CORTEXDB_SCOPE` = `org:<org>/team:<team>` (required; a root scope is refused, by design).

## 1. Prerequisites

Verify, and stop with a clear message if missing:

```bash
docker info >/dev/null 2>&1 && echo docker-ok || echo docker-missing   # only if starting a server
python3 --version                                                      # 3.10+
cortexdb-mcp --version || pip install cortexdb-mcp                     # needs >= 0.8.0 for code tools
```

If `CORTEXDB_URL` is set, skip to section 3.

## 2. Start the server (code plane on)

```bash
docker run -d --name cortexdb-codeplane \
  -p 127.0.0.1:3142:3141 \
  -e CORTEX_CODE_PLANE=1 \
  -e CORTEX_CODE_WATCH=1 \
  -e CORTEX_CODE_BUNDLE=1 \
  -e CORTEX_CODE_REPO_ROOTS=/repos \
  -e CORTEX_API_KEY="${CORTEXDB_API_KEY}" \
  -v cortexdb_code_data:/data \
  -v "${PROJECT_DIR}:/repos/$(basename "${PROJECT_DIR}"):ro" \
  cortexdb/cortexdb:v0.10.5
```

Wait for health, up to two minutes:

```bash
until curl -fsS -m 2 http://127.0.0.1:3142/v1/health >/dev/null; do sleep 2; done && echo healthy
```

No embedding key is needed for the code plane. If the user also wants memory features in this session, the server additionally needs embedding environment (`CORTEX_EMBEDDING_*`); otherwise `memory_search` answers from events only, and every code tool works.

## 3. Register the repository

Registration indexes synchronously and reports fact counts:

```bash
curl -fsS -X POST http://127.0.0.1:3142/v1/code/repos \
  -H "Authorization: Bearer ${CORTEXDB_API_KEY}" \
  -H "X-Cortex-Actor: ${CORTEXDB_ACTOR}" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"$(basename "${PROJECT_DIR}")\",\"path\":\"/repos/$(basename "${PROJECT_DIR}")\",\"scope\":\"${CORTEXDB_SCOPE}\"}"
```

Expected: JSON with `stats.files`, `stats.definitions`, `stats.facts`. A `409 REPO_EXISTS` means the name is taken: delete it first (`DELETE /v1/code/repos/<name>`) or pick another name. A `422 REPO_PATH_NOT_ALLOWED` means the path is outside the server's `CORTEX_CODE_REPO_ROOTS`.

## 4. Wire your harness (Claude Code)

Write `.mcp.json` in `PROJECT_DIR`:

```json
{
  "mcpServers": {
    "cortexdb": {
      "type": "stdio",
      "command": "cortexdb-mcp",
      "env": {
        "CORTEXDB_URL": "http://127.0.0.1:3142",
        "CORTEXDB_API_KEY": "<same key as the server>",
        "CORTEXDB_ACTOR": "<actor>",
        "CORTEXDB_SCOPE": "<org/team scope>"
      }
    }
  }
}
```

Then append the block from `PACK/rules-block.md` to `PROJECT_DIR/CLAUDE.md` (create the file if absent). The user restarts Claude Code in that directory to load the MCP server; a headless `-p` run picks it up automatically.

## 5. Prove it (smoke)

1. Tool surface: the `cortexdb` MCP server lists `code_explore`, `code_impact`, `code_inventory`, `code_graph` (plus memory tools).
2. Explore: `code_explore` with `{"query": "entry point and main flow of this repository", "repo": "<name>", "token_budget": 900}` returns cited snippets `repo:path@<hash>#Lstart-Lend`.
3. Impact: `code_impact` on a symbol the repository actually defines returns `reached` entries with hops and `weakest_tier`.
4. Envelope honesty: `files_considered`, `files_included` and `tokens_used` are present; anything unindexed appears in `uncertainty`, never guessed.

Report the three outputs to the user, trimmed.

## 6. Grow and leave (for later, do not run now)

- Second repo on the same server: mount it read-only under `/repos` and POST `/v1/code/repos` again with the same team scope. Cross-repo questions use one `code_explore` with `repos`.
- Leaving: `PACK/exit.md` and `PACK/demo/cortexdb-code eject`.

## Do not

- Do not run `cortexdb init` or any signup; that mints a new identity. This pack uses the server the user pointed at.
- Do not disable the read-only mount, and do not register paths outside `/repos`.
- Do not invent endpoints. The code plane's routes live under `/v1/code/*`; the canonical reference ships inside the server image at `/opt/cortexdb/docs/CODE_PLANE.md` (read it with `docker exec <container> cat ...`). The legacy `/v1/remember` route does not exist; it was never part of v1.
- Do not print or commit the API key, `.env`, or `.mcp.json` with a real key in a public repo.

## Sibling

For memory-plane onboarding of an app in a repo, use `../02-app-in-repo/`. For attaching a chat harness to an existing brain, `../03-harness-attach/`. This track is the code plane; both other tracks compose with it on the same server.
