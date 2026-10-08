# GitHub history into team memory

The code plane answers "where is it and what depends on it". Memory answers "why is it like this and who decided". The fastest way to fill memory for a repository is the GitHub connector: pull requests, issues, comments, reviews and pushes, stored with provenance and linked into the code graph as bridge facts (`discussed_in`, `changed_by`) when the connector version supports code anchors.

## One-shot sync

```bash
pip install cortexdb-connectors PyGithub

export GITHUB_TOKEN=<read-only token>
export GITHUB_REPOS=<org>/<repo>
export GITHUB_BACKFILL_DAYS=30
export GITHUB_EVENTS=pull_request,issues,pull_request_review,issue_comment,pull_request_review_comment,push

cortexdb-sync \
  --api-url http://<team-server>:3142 \
  --api-key <team-key> \
  --actor user:<name> \
  --scope-template "org:<org>/team:<team>/source:github-{repo}" \
  --state-file sync-state-github.json \
  sync github
```

Notes verified against cortexdb-connectors 0.2.22:

- The connector name (`github`) comes after the global flags; `cortexdb-sync sync github --api-url ...` is rejected. Global flags go first.
- `GITHUB_EVENTS` uses the feed kind names listed above (`pull_request`, not `pull_requests`; `issue_comment`, not `comments`).
- `GITHUB_BACKFILL_DAYS` defaults to 30; each later sync re-reads the last 6 hours.
- `--scope-template` supports `{repo}` placeholders; scoping per source keeps GitHub content addressable and erasable as a unit.
- Use 0.2.22 or newer: older versions stored most GitHub content empty and re-key records, so a re-sync is needed after upgrading.

## What it gives the agent

After a sync, `memory_search` in the repo's team scope returns PR titles, bodies and discussion excerpts, with authors and timestamps. Questions that used to be unanswerable mid-session ("was there a reason this check exists?") get answered with the actual PR, its author, and the review thread.

## Keep it fresh

Run the same command on a schedule (cron, CI, or `cortexdb-sync ... watch github`) with the same state file; it resumes from its cursor. A webhook receiver (`serve`) exists for real-time ingestion when GitHub can reach your server.

## Honesty

- Sync stores what GitHub's API returns: edited PR bodies are the edited versions, deleted comments are gone. It is a mirror of the present, not an archive.
- Backfills are rate-limited by GitHub; widen `GITHUB_BACKFILL_DAYS` gradually, not by orders of magnitude.
