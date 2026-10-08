# Demo and measurement harness

Everything in this folder was run, not sketched. It is the tooling for two things: onboarding in one line, and measuring your agent with vs without the layer.

## Lifecycle CLI: `cortexdb-code`

```bash
bash cortexdb-code init        # server up (if needed), repo indexed, Claude Code wired, verified
bash cortexdb-code add ../other-repo   # second repo, same server, same scope
bash cortexdb-code status      # server + repos + wiring health
bash cortexdb-code doctor      # what is broken and what to run
bash cortexdb-code eject       # exports (memory, index bundle, graph), removes repo, unwires agent
```

Configuration via env: `CORTEXDB_URL`, `CORTEXDB_API_KEY`, `CORTEXDB_ACTOR`, `CORTEXDB_SCOPE`. `init` starts a local server (code plane on, localhost only) when `CORTEXDB_URL` is not already serving.

## On-camera meter: `statusline.sh`

A Claude Code status line showing model, dollars, context percentage and cache/in/out tokens, updated every turn. Set in the project's `.claude/settings.json`:

```json
{"statusLine": {"type": "command", "command": "bash <path>/statusline.sh"}}
```

## A/B runner: `ab_runner.py`

Two clones or worktrees of the same commit: one stock, one with `.mcp.json` + the rules block (and its repo registered on the server). Same prompt, same model, fresh session per run, auto memory disabled on both arms, repo reset between runs, one CSV row per run (input / cache read / cache write / output tokens, cost, turns, wall time, tool mix, files read and edited, MCP call count).

```bash
python3 ab_runner.py --dir-a ../myrepo-a --dir-b ../myrepo-b --tasks tasks.json --runs 5 --out ab.csv
```

Read medians, not single runs: agent variance is high, and cache-read tokens dominate session totals, so report fresh input, cache read, cache write and output separately.

## Honesty rules for publishing any number out of this

- Same Claude Code build, same model, same flags, cold session per run.
- Report medians and ranges over N runs, N at least 3, with the repo and task set named.
- The rules block is part of the treatment arm; give the control arm an equivalent "search narrowly" line in its CLAUDE.md so the rules file itself is not the difference.
- Index time is one-off; show it once, do not fold it into per-task numbers.
- If a run was contaminated (agent escaped its directory, server error mid-run), mark it in the CSV, do not delete it silently.
