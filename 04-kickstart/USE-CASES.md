# Use cases — the bare basics, with links for depth

The handful of patterns that cover most enterprise workloads. Each has the minimal
call shape and the doc page that goes deep. Copy-paste REST versions of all of these
live in [`../examples/`](../examples/).

---

## 1. Support-agent memory (ticket-resolution recall)

**Problem:** every new ticket starts from zero; the answer lives in closed tickets.

**Pattern:** backfill closed tickets as experiences, then on each new ticket recall
the relevant history and generate a grounded draft comment.

```bash
# One-time: load ticket history (each item = one write)
curl -X POST "$CORTEXDB_URL/v1/experience" \
  -H "Authorization: Bearer $CORTEXDB_API_KEY" -H "X-Cortex-Actor: $CORTEXDB_ACTOR" \
  -H "Content-Type: application/json" \
  -d '{ "scope": "org:acme/source:zendesk",
        "modality": "document",
        "content": { "kind": "text", "text": "Ticket #8821: refund not received after 10 days. Category: refunds. Resolved: duplicate charge, refunded." },
        "context": { "observed_at": "2026-07-14T09:30:00Z" } }'

# Day-to-day: draft the comment with citations
curl -X POST "$CORTEXDB_URL/v1/answer" \
  -H "Authorization: Bearer $CORTEXDB_API_KEY" -H "X-Cortex-Actor: $CORTEXDB_ACTOR" \
  -H "Content-Type: application/json" \
  -d '{ "scope": "org:acme", "view": "descend",
        "question": "How have we resolved refund-not-received tickets?" }'
```

Docs: [answer](https://cortexdb.ai/docs/api-reference/answer) ·
[experience](https://cortexdb.ai/docs/api-reference/experience)

## 2. Cross-source company memory

**Problem:** the answer spans Slack, Jira, the wiki, and the ticket system — no
single tool can query them together.

**Pattern:** sync each source into its own `source:` lane; one `descend` recall or
answer rolls them all up.

```
org:acme
├── source:slack        # channels / threads
├── source:jira         # issues / bugs
├── source:notion       # docs / wikis
└── source:zendesk      # support tickets
```

```bash
curl -X POST "$CORTEXDB_URL/v1/recall" \
  -H "Authorization: Bearer $CORTEXDB_API_KEY" -H "X-Cortex-Actor: $CORTEXDB_ACTOR" \
  -H "Content-Type: application/json" \
  -d '{ "scope": "org:acme", "view": "descend",
        "query": "Which ticket categories are also escalated on Slack and tracked as Jira bugs?" }'
```

Connectors (18 sources, self-hosted `cortexdb-sync` or managed): Slack, GitHub,
GitLab, Jira, Freshdesk, tl;dv, Linear, Confluence, Notion, PagerDuty, Discord,
Microsoft Teams, Google Workspace, Salesforce, HubSpot, Zendesk, Intercom,
ServiceNow. Each writes into `<root>/source:<connector>`.
Docs: [connectors](https://cortexdb.ai/docs/connectors)

## 3. Per-user / per-account memory in your product

**Problem:** your app's AI features should remember each customer's history.

**Pattern:** scope by user under your org; reads never cross users.

```bash
curl -X POST "$CORTEXDB_URL/v1/experience" \
  -H "Authorization: Bearer $CORTEXDB_API_KEY" -H "X-Cortex-Actor: $CORTEXDB_ACTOR" \
  -H "Content-Type: application/json" \
  -d '{ "scope": "org:acme/app:myproduct/user:alice",
        "modality": "conversation",
        "content": { "kind": "message", "role": "user",
                     "text": "Upgraded to the Team plan; invoicing monthly." } }'
```

A bot writing on behalf of a user (or memory about a third party) sets the
envelope's identity slots (observed actor / subject) — doing so requires the
`scope.write.on_behalf_of` / `scope.write.about_other` capabilities.
Docs: [experience envelope](https://cortexdb.ai/docs/concepts/experience-envelope) ·
[scopes](https://cortexdb.ai/docs/concepts/scopes)

## 4. "What did we know on date X?" — time travel for audit & compliance

**Problem:** regulators (or a dispute) ask what your system believed at a past date.

**Pattern:** every derived fact is bi-temporal (valid time vs. recorded time) and
nothing is overwritten — corrections close the old record and append a new one.

```bash
# What was true in the world, and what did we know, on 1 March?
curl -X POST "$CORTEXDB_URL/v1/recall" \
  -H "Authorization: Bearer $CORTEXDB_API_KEY" -H "X-Cortex-Actor: $CORTEXDB_ACTOR" \
  -H "Content-Type: application/json" \
  -d '{ "scope": "org:acme", "view": "descend", "query": "acme deal stage",
        "temporal": { "as_of": "2026-03-01" } }'

# Full correction history of one claim
curl "$CORTEXDB_URL/v1/facts/timeline?scope=org:acme&subject=ent_acme_corp&predicate=deal_stage" \
  -H "Authorization: Bearer $CORTEXDB_API_KEY" -H "X-Cortex-Actor: $CORTEXDB_ACTOR"
```

Docs: [bi-temporal](https://cortexdb.ai/docs/concepts/bi-temporal) ·
[facts](https://cortexdb.ai/docs/api-reference/facts)

## 5. Deletion & GDPR / DSAR

**Problem:** a data subject asks to be forgotten; a user retracts a statement.

**Pattern:** two routes. `forget` = operational deletion (drop derived layers, or
redact events, with audit). `erasures` = the GDPR flow that removes events from the
WAL — always **preview → execute → poll**.

```bash
# Preview (nothing changes; returns per-layer estimates + preview_id)
curl -X POST "$CORTEXDB_URL/v1/erasures/preview" \
  -H "Authorization: Bearer $CORTEXDB_API_KEY" -H "X-Cortex-Actor: $CORTEXDB_ACTOR" \
  -H "Content-Type: application/json" \
  -d '{ "scope": "org:acme/app:myproduct/user:alice", "confirm_all": true,
        "audit_note": "DSR #1234 — preview" }'

# Execute with the returned preview_id, then poll status until completed
```

Every forget writes a tamper-evident, hash-chained audit row; send `X-Request-Id`
to tie the audit row to your request logs.
Docs: [forget](https://cortexdb.ai/docs/api-reference/forget) ·
[erasures](https://cortexdb.ai/docs/api-reference/erasures) ·
[audit trail](https://cortexdb.ai/docs/enterprise/audit-trail)

## 6. Document / media archive (PDFs, images, audio)

Upload bytes to `POST /v1/blobs` (32 MiB cap), then write an experience that carries
the blob reference **and its text** — recall only searches text. Supplying the
transcript yourself skips the server's vision/Whisper cost. Untranscribed blobs are
processed in the background once processors are configured.
Docs: [media ingestion](https://cortexdb.ai/docs/features/media-ingestion)

## 7. Code-aware memory for engineering teams

Index repos (`CORTEX_CODE_PLANE=1`, `cortexdb code add <path>`) and query cited
code context (`repo:path@hash#Lx-Ly`) alongside normal memory.
Docs: [code plane](https://cortexdb.ai/docs/features/code-plane)

---

## Reliability patterns worth knowing early

- **Idempotency keys** on every write from a pipeline: same key + same body = no-op;
  same key + different body = `409 IDEMPOTENCY_CONFLICT`. Keys expire after ~24 h.
- **After a backfill**, gate quality checks on `GET /v1/derivation/status?scope=…`
  → `caught_up: true`. For single writes use `?wait=indexed`.
- **Error bodies are flat**: `error_code`, `message`, `retriable`, `request_id`.
  `retriable: true` → resend the identical request; `false` → fix the request.
  [errors](https://cortexdb.ai/docs/api-reference/errors)
