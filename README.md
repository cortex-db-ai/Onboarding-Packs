# CortexDB Onboarding Packs

[![Docs hygiene](https://github.com/vkhatana-cortexdb/Onboarding-Packs/actions/workflows/hygiene.yml/badge.svg)](https://github.com/vkhatana-cortexdb/Onboarding-Packs/actions/workflows/hygiene.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

Official onboarding docs for CortexDB. **One repo, clear paths.** Send this whole repo (or a folder deep-link). Do not fork into three repos — that goes stale.

---

## Pick your path (read this first)

| Priority | Who you are | What to say / do | Open |
|---|---|---|---|
| **1 — top** | **Human** on **cloud / free trial** (or you already have hosted keys) | Get keys → smoke write/recall yourself → then build an app with the same `.env` | [`00-cloud-trial/`](00-cloud-trial/) → `CLOUD-TRIAL.md` |
| **2** | **Human** who wants **Docker self-host** | Local container trial | [`01-self-host/`](01-self-host/) → `CORTEXDB_SETUP_GUIDE.md` |
| **3** | **Agentic developer** building a **new** app | *“Build my app with CortexDB”* (prefer shared cloud `.env` from path 1) | [`02-app-in-repo/APP-ONBOARDING.md`](02-app-in-repo/APP-ONBOARDING.md) |
| **4** | **Agentic development** on an **existing** repo | *“Implement CortexDB on my current repo”* | Same `APP-ONBOARDING.md` + `PROJECT_DIR` |
| **5** | Hook tools to a **personal / shared brain** | Attach Claude Code, Claude Desktop, Cursor, or Grok Bot | [`03-harness-attach/`](03-harness-attach/) |

Agents: also read [`AGENTS.md`](AGENTS.md).

**Typical “try CortexDB then build” flow:** path **1** then path **3** (same keys). Skip Docker unless they ask.

---

## 1. Cloud / free trial (default playground)

Hosted at `https://api-v1.cortexdb.ai`.

1. Open **[`00-cloud-trial/`](00-cloud-trial/)**.
2. Follow **`CLOUD-TRIAL.md`**: anonymous signup (7-day free tier) **or** paste existing cloud keys.
3. Run whoami + smoke write/answer yourself.
4. Keep `.env` gitignored. Then jump to [`02-app-in-repo/`](02-app-in-repo/) with `SHARE_BRAIN=true`.

Docs cold-start: https://cortexdb.ai/docs/sdks/rest-api

---

## 2. Self-host (Docker) — optional

Only if you want a container on your machine.

Open [`01-self-host/`](01-self-host/) → `CORTEXDB_SETUP_GUIDE.md`.

---

## 3–4. Build or cortexdbify an app

[`02-app-in-repo/APP-ONBOARDING.md`](02-app-in-repo/APP-ONBOARDING.md)

> Build my app with CortexDB. Use `02-app-in-repo/`. Prefer `00-cloud-trial/.env` as the shared brain.

> Implement CortexDB on my current repo. Pack = `02-app-in-repo/`. `PROJECT_DIR` = this repository. `SHARE_BRAIN=true` if I already have cloud keys.

---

## 5. Personal / shared brain — harnesses

[`03-harness-attach/`](03-harness-attach/) — Claude Code (`~/.claude.json`), Claude Desktop (`claude_desktop_config.json`), Cursor, Grok Bot.

---

## Folder map

```
Onboarding-Packs/
  README.md
  AGENTS.md
  CONTRIBUTING.md     ← how to file issues / send PRs
  SECURITY.md         ← private vulnerability reporting
  00-cloud-trial/     ← hosted free trial / cloud keys (default human start)
  01-self-host/       ← Docker local trial
  02-app-in-repo/     ← new app or existing repo (uses keys from 00 or 01)
  03-harness-attach/  ← wire IDE/chat to a brain
```

---

## Honesty (claims)

- Integrations: **47** (not 53).
- Do **not** cite LongMemEval **93.8%**.
- Do **not** cite **~742ms** as a latency claim.
- **Raft** is experimental / not marketed as shipped.
- CortexDB is **not** “always-on” without setup.
- Free-tier anonymous tokens expire (~7 days); re-signup is a new empty tenant.

## Contributing

**Issues and PRs are very welcome.** If a command in here failed on your machine, that's a
bug worth filing — you don't need permission or an affiliation to open one.

- Report a broken step or wrong claim → [open an issue](https://github.com/vkhatana-cortexdb/Onboarding-Packs/issues/new/choose)
- Send a fix → fork, branch, PR against `main`. See [CONTRIBUTING.md](CONTRIBUTING.md).
- `main` is protected: every change lands through a reviewed PR, maintainers included.
- Participation is governed by our [Code of Conduct](CODE_OF_CONDUCT.md).

Corrections backed by real terminal output get merged fastest. Please open an issue before a
large restructure so we can agree on the shape first.

## Security

- Never commit filled `.env` / `cortex.env`.
- Example env files stay placeholders only.
- Agents must not print API keys or paste them into chat.
- Found a vulnerability or a committed secret? **Do not open a public issue** —
  follow [SECURITY.md](SECURITY.md).

## License

[Apache License 2.0](LICENSE).
