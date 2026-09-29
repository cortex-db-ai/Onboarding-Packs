# 02 — Wire CortexDB into an app / repo

Drop CortexDB into an **existing or new application repository** as a dual-write memory layer. The app’s primary DB stays; CortexDB sits alongside it.

## What's here

| File | Role |
|---|---|
| **`APP-ONBOARDING.md`** | Executable agent script — start here for an agent. |
| **`AGENTS.md`** | Hard rules for coding agents in the target repo. |
| **`CONVENTIONS.md`** | Scopes, views, dual-write conventions (goes to `.cortexdb/`). |
| **`docs/`** | Offline doc pack (`00_INDEX` + 01–03; `04` may be a pointer). |

## Hand to an agent

```text
Follow 02-app-in-repo/APP-ONBOARDING.md.
PROJECT_DIR=<absolute path to my app repo>
SHARE_BRAIN=true
CORTEX_ENV_FILE=<path to complete CortexDB .env>
Do not print tokens. Dual-write only — do not replace my existing DB.
```

## Audience

- **Backend / product engineers** wiring memory into a real app.
- **Agents** that can edit a repo and run shell checks.

Not for standing up the CortexDB server itself (use `01-self-host/`) or attaching chat/IDE harnesses only (use `03-harness-attach/`).

Worked API examples for every call the onboarding makes — store, recall, answer, layer
reads, erasure, in REST/Python/TypeScript — live in [`../examples/`](../examples/).
Never invent endpoints beyond those.
