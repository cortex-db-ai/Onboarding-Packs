# CortexDB — Cloud hosting (free trial or managed instance)

Two ways to get a hosted brain. Both speak the same `/v1` REST API — only identity
and TTL differ. Follow as a **human**, or hand to a coding agent. Do not print
tokens. Do not commit `.env`.

`PACK` = this folder (`00-cloud/`).

Official cold-start: https://cortexdb.ai/docs/sdks/rest-api
Ready-made API examples (store / recall / answer / forget): [`../examples/`](../examples/)

---

## 0. Pick your access mode

| Mode | When | Identity | TTL |
|---|---|---|---|
| **A — Free trial** | You have nothing yet, want a playground now | Anonymous signup — no email, no card | **7 days**, then gone |
| **B — Managed cloud instance** | You are a team / pilot customer | Dedicated tenant URL + API key delivered separately over a secure channel | Persistent — no expiry |

If a working `.env` already exists in `PACK`, use it. Never mint over a working tenant.

---

## Mode A — Free trial (anonymous signup)

Needs `curl` and `jq`.

```bash
cd "$PACK"
cp env.example .env
chmod 600 .env

SIGNUP=$(curl -sfS -X POST https://api-v1.cortexdb.ai/v1/auth/signup \
  -H 'Content-Type: application/json' -d '{}')

# Show metadata only (no token)
echo "$SIGNUP" | jq '{user_id, scope, expires_at}'

# Write .env without printing the bearer
python3 -c "
import json, os, pathlib
s = json.loads('''$SIGNUP''')
p = pathlib.Path('.env')
p.write_text(
    'CORTEXDB_URL=https://api-v1.cortexdb.ai\n'
    f\"CORTEXDB_API_KEY={s['token']}\n\"
    f\"CORTEXDB_ACTOR={s['user_id']}\n\"
    f\"CORTEXDB_SCOPE={s['scope']}\n\"
    + (f\"# CORTEXDB_EXPIRES_AT={s.get('expires_at','')}\n\" if s.get('expires_at') else '')
    + '# SOURCE=free-tier-signup\n'
)
p.chmod(0o600)
print('wrote .env mode 0600')
print('actor:', s['user_id'])
print('scope:', s['scope'])
print('expires_at:', s.get('expires_at'))
"
```

Free-tier TTL is **7 days**. Re-signup mints a **new** empty tenant. Prefer Mode B
(or dashboard keys) for anything you want to keep.

## Mode B — Managed cloud instance (dedicated tenant)

For pilot/team deployments CortexDB provisions a **dedicated instance** with its own
URL, scope root, and actor. Customer-specific onboarding packs are delivered directly
and privately — they are intentionally not published in this public repo. You get:

| Item | Shape | Example |
|---|---|---|
| Base URL | `https://<tenant>.cortexdb.ai` | assigned by CortexDB at provisioning |
| API key | `<YOUR_API_KEY>` — delivered separately over a secure channel | sent on every call: `Authorization: Bearer <YOUR_API_KEY>` |
| Actor header | `X-Cortex-Actor: agent:<tenant>` (or `user:<you>`) | agreed with CortexDB at provisioning |
| Scope root | `org:<tenant>` (+ subtrees per team / source / customer) | assigned to match your tenant |
| Health | open, no key | `GET /v1/admin/health` → `{"status":"healthy"}` |

To request one, contact your CortexDB contact. When the key arrives:

```bash
cd "$PACK"
cp -n env.example .env
chmod 600 .env
```

Edit `.env`:

- `CORTEXDB_URL=https://<tenant>.cortexdb.ai`
- `CORTEXDB_API_KEY=` the delivered Bearer token
- `CORTEXDB_ACTOR=` the actor agreed in the access table (must match the token subject)
- `CORTEXDB_SCOPE=` your scope root, e.g. `org:<tenant>`

Never commit the key or paste it into chat, tickets, or email.

Dashboard `cx_live_…` keys are for dashboard/MCP BFF flows. For this REST smoke test
you need a **Bearer** token. Do not invent exchange endpoints.

---

## 1. whoami (both modes)

```bash
set -a && source .env && set +a

curl -sfS "$CORTEXDB_URL/v1/auth/whoami" \
  -H "Authorization: Bearer $CORTEXDB_API_KEY" \
  -H "X-Cortex-Actor: $CORTEXDB_ACTOR"
```

If you see `actor_mismatch`, fix `CORTEXDB_ACTOR`. Do not print the bearer.

## 2. Smoke: write + answer (both modes)

```bash
set -a && source .env && set +a
NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)
IDEM="cloud-smoke-$(date +%s)"

curl -sfS -X POST "$CORTEXDB_URL/v1/experience" \
  -H "Authorization: Bearer $CORTEXDB_API_KEY" \
  -H "X-Cortex-Actor: $CORTEXDB_ACTOR" \
  -H 'Content-Type: application/json' \
  -d "{
    \"scope\": \"$CORTEXDB_SCOPE\",
    \"modality\": \"conversation\",
    \"content\": { \"kind\": \"message\", \"role\": \"user\",
                   \"text\": \"Onboarding smoke: Q3 revenue exceeded 2.4M, up 34% YoY\" },
    \"context\": { \"observed_at\": \"$NOW\" },
    \"idempotency_key\": \"$IDEM\"
  }"

curl -sfS -X POST "$CORTEXDB_URL/v1/answer" \
  -H "Authorization: Bearer $CORTEXDB_API_KEY" \
  -H "X-Cortex-Actor: $CORTEXDB_ACTOR" \
  -H 'Content-Type: application/json' \
  -d "{
    \"scope\": \"$CORTEXDB_SCOPE\",
    \"question\": \"What was Q3 revenue?\",
    \"view\": \"holistic\",
    \"diagnostics\": \"none\"
  }"
```

Success = whoami works and answer mentions the smoke write. You have a working cloud
brain. More patterns — recall views, layer reads, SDKs, erasure — live in
[`../examples/`](../examples/).

## 3. Next: build the app (same keys)

Skip `01-self-host` unless you want Docker.

### New app

> Build my app with CortexDB. Shared brain at `00-cloud/.env`. Follow `02-app-in-repo/APP-ONBOARDING.md`. `SHARE_BRAIN=true`. Do not mint a new tenant. Do not print tokens.

### Existing repo

> Implement CortexDB on my current repo. `CORTEX_ENV_FILE` = absolute path to `00-cloud/.env`. `SHARE_BRAIN=true`. Follow `APP-ONBOARDING.md`. Dual-write only.

Optional: same `.env` → `03-harness-attach/` for Claude / Cursor / Grok.

Standing rule once wired: recall → act → write. Look up APIs from docs; never invent `/v1/remember`.

---

## Honesty + security

- Integrations: **47**. No fake LongMemEval / latency claims. Raft experimental.
- Free trial ≠ permanent account. 7-day tokens expire; re-signup = new empty tenant.
- Managed instances are provisioned by CortexDB — no self-service URL guessing.
- Never commit `.env`. Never paste `CORTEXDB_API_KEY` into chat, tickets, or email.
