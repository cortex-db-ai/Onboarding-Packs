> **Pack track:** `00-cloud` — get a hosted CortexDB brain (free trial **or** managed cloud instance), prove write/recall, then build an app with it.

# Cloud hosting — free trial or managed instance

**Default human playground** if you do not want Docker.

Two access modes, one API:

1. **Free trial (anonymous signup)** — `POST /v1/auth/signup` with `{}`. No email, no card. **7-day** token at `https://api-v1.cortexdb.ai`.
2. **Managed cloud instance (dedicated tenant)** — `https://<tenant>.cortexdb.ai` with an API key delivered separately. Persistent identity for teams; pilot customers receive their pack directly and privately (not in this repo).

Get credentials, smoke-test them yourself, then point `02-app-in-repo/` (or your agent) at the same `.env` to build the app.

| File | What it is |
|---|---|
| **`CLOUD.md`** | Step-by-step for both modes. Start here. |
| **`env.example`** | Env template. Copy to `.env` (gitignored). |
| **`README.md`** | This file. |

Self-host Docker instead: [`../01-self-host/`](../01-self-host/).

## After keys work

1. Follow the `CLOUD.md` smoke test.
2. Browse [`../examples/`](../examples/) — store, recall, answer, layer reads, SDKs, erasure.
3. Build / cortexdbify: [`../02-app-in-repo/APP-ONBOARDING.md`](../02-app-in-repo/APP-ONBOARDING.md) with `SHARE_BRAIN=true` and `CORTEX_ENV_FILE` = this folder's `.env`.
4. Optional harnesses: [`../03-harness-attach/`](../03-harness-attach/).
