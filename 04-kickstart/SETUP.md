# Setup — what to define before your first write

You can be writing memories in five minutes. But five **decisions** determine whether
your data lands in a shape you'll still like in a year. Make them first — everything
else is commands.

> Full docs: [scopes](https://cortexdb.ai/docs/concepts/scopes) ·
> [authorization](https://cortexdb.ai/docs/concepts/authorization) ·
> [self-hosting defaults](https://cortexdb.ai/docs/self-hosting/defaults) ·
> [configuration](https://cortexdb.ai/docs/operations/configuration)

---

## Decision 1 — Where does your brain run?

| Option | Pick it if | How |
|---|---|---|
| **Cloud free trial** | You want a playground now | Anonymous signup, 7-day token — [`../00-cloud/CLOUD.md`](../00-cloud/CLOUD.md) Mode A |
| **Managed instance** | Team / production, persistent identity | Dedicated `https://<tenant>.cortexdb.ai`, key delivered securely — [`../00-cloud/CLOUD.md`](../00-cloud/CLOUD.md) Mode B |
| **Self-hosted Docker** | Data must not leave your network | One `docker run`, `http://localhost:3141` — [`../01-self-host/`](../01-self-host/) |

Whichever you pick, the API is the same `/v1` surface. Put the credentials in a
gitignored `.env` (`CORTEXDB_URL`, `CORTEXDB_API_KEY`, `CORTEXDB_ACTOR`,
`CORTEXDB_SCOPE`) — every later step (app build, harness attach) reuses it.

## Decision 2 — Your scope tree (the one you can't easily undo)

Memory is organized as a `/`-delimited path of `type:id` segments, e.g.
`org:acme/dept:support/user:alice`. Two hard rules and one convention:

- **Every segment needs a colon** — `org:acme`, not `acme` (bare word → `422`).
- **Use allowed types**: `org, dept, team, app, user, agent, service, ws, project,
  global, system, source` (custom types must be registered first, else
  `422 UNREGISTERED_SCOPE_TYPE`).
- Convention: **≤ 8 segments, ≤ 64 chars per segment**.

Pick a layout that matches how you'll *query*, because recall reads scopes:

```
org:acme                     ← org-wide shared knowledge
org:acme/source:slack        ← one lane per connected source (connector convention)
org:acme/dept:support/user:alice   ← per-user memory under a team
org:acme/ws:q3-launch        ← cross-functional project workspace
```

- `view:"granular"`/`local` reads one scope; `holistic` reads the scope **and its
  ancestors**; `descend` rolls up the scope **and everything beneath it**.
- Scopes auto-provision on first write; register them explicitly (`POST /v1/scopes`)
  only when you need members and policies.

**Enterprise multi-tenancy:** isolation comes from the token's `aud` claim — a
request can never see another tenant's data. The `cloud_shared_saas` deployment
preset enforces this posture (it works self-hosted too; the prefix names the posture,
not the hosting). Verify yours with `GET /v1/auth/whoami` → `tenant_id`,
`deployment_preset`. ([multi-tenancy](https://cortexdb.ai/docs/enterprise/multi-tenancy))

## Decision 3 — Embeddings (pinned to the data volume — choose once, before the first write)

Every stored memory becomes a vector. The choice is pinned to the data directory;
changing dimensions later requires an offline rebuild.

| | **Local (Ollama)** | **API (default: `text-embedding-3-small`, 1536 dims)** |
|---|---|---|
| Cost | $0 | $0.02 per million tokens — negligible |
| Accuracy | ~3–5 points below the API default on benchmark | Default reference |
| Pick it if | Data must stay on-prem, or the host has spare CPU/RAM/GPU | Modest hardware, fewer moving parts |

([embeddings](https://cortexdb.ai/docs/operations/embeddings))

## Decision 4 — Enrichment on or off?

CortexDB's five layers: **Events** (raw, immutable, always on) and the derived
**Episodes / Facts / Beliefs / Understanding** (built by a background scheduler
using an LLM). On a bare self-hosted instance **the derived layers are empty until
enrichment is configured** — raw events and vector search still work.
([layers](https://cortexdb.ai/docs/concepts/layers) ·
[defaults](https://cortexdb.ai/docs/self-hosting/defaults))

- Off = cheap archival + search. On = facts/beliefs/timelines — this is where the
  per-event LLM spend goes (see [`COSTS.md`](COSTS.md)).
- Timing (write barriers, from the lifecycle doc): capture is durable in ~10 ms
  (fsync'd); `?wait=indexed` returns in ~100–500 ms; `?wait=consolidated` in
  ~0.5–3 s. Derived layers build asynchronously in a background scheduler — gate
  on `GET /v1/derivation/status?scope=…` → `caught_up: true` after backfills, and
  expect Understanding to lag real-time by minutes to hours
  ([lifecycle](https://cortexdb.ai/docs/concepts/lifecycle) ·
  [layers](https://cortexdb.ai/docs/concepts/layers)).

## Decision 5 — Answer lane

`POST /v1/answer` (recall + LLM with citations) needs an answer model configured
(self-hosted: the `CORTEX_ANSWER_*` lane). Without it, `/v1/recall` still works —
use recall and generate answers yourself. ([answer](https://cortexdb.ai/docs/api-reference/answer))

---

## Prove it works (2 minutes)

```bash
set -a && source .env && set +a

# 1. Who am I?
curl -sfS "$CORTEXDB_URL/v1/auth/whoami" \
  -H "Authorization: Bearer $CORTEXDB_API_KEY" \
  -H "X-Cortex-Actor: $CORTEXDB_ACTOR"

# 2. Write one memory (wait=indexed blocks until searchable, ~100–500 ms)
curl -sfS -X POST "$CORTEXDB_URL/v1/experience?wait=indexed" \
  -H "Authorization: Bearer $CORTEXDB_API_KEY" \
  -H "X-Cortex-Actor: $CORTEXDB_ACTOR" \
  -H "Content-Type: application/json" \
  -d "{
    \"scope\": \"$CORTEXDB_SCOPE\",
    \"modality\": \"conversation\",
    \"content\": { \"kind\": \"message\", \"role\": \"user\",
                  \"text\": \"Setup check: we ship the payments migration on 2026-11-02.\" }
  }"

# 3. Read it back
curl -sfS -X POST "$CORTEXDB_URL/v1/recall" \
  -H "Authorization: Bearer $CORTEXDB_API_KEY" \
  -H "X-Cortex-Actor: $CORTEXDB_ACTOR" \
  -H "Content-Type: application/json" \
  -d "{ \"scope\": \"$CORTEXDB_SCOPE\", \"view\": \"holistic\",
        \"query\": \"When do we ship the payments migration?\" }"
```

Then load real data — connectors for 18 sources (Slack, Jira, GitHub, Notion,
Freshdesk, Zendesk, Salesforce, HubSpot, Google Workspace, …) via
`cortexdb-sync`, or `cortexdb import` for flat files:
[connectors](https://cortexdb.ai/docs/connectors) ·
[CLI](https://cortexdb.ai/docs/sdks/cli). After a backfill, poll
`GET /v1/derivation/status?scope=<scope>` until `caught_up: true` before judging
answer quality ([derivation status](https://cortexdb.ai/docs/api-reference/derivation-status)).

More copy-paste examples: [`../examples/`](../examples/).
