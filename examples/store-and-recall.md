# REST examples — store, recall, answer, layer reads, erase

Source: https://cortexdb.ai/docs/sdks/rest-api (verified live 2026-09). All calls
need `Authorization: Bearer $CORTEXDB_API_KEY` and `X-Cortex-Actor: $CORTEXDB_ACTOR`
(actor must match the token's `sub` claim, else `401 ACTOR_MISMATCH`).

---

## 0. Mint a free trial token (no email, no card)

```bash
# Returns token + user_id + scope + 7-day expiry
SIGNUP=$(curl -sfS -X POST https://api-v1.cortexdb.ai/v1/auth/signup \
  -H 'Content-Type: application/json' -d '{}')
export CORTEXDB_API_KEY=$(echo "$SIGNUP" | jq -r .token)
export CORTEXDB_ACTOR=$(echo "$SIGNUP" | jq -r .user_id)
export CORTEXDB_SCOPE=$(echo "$SIGNUP" | jq -r .scope)
```

## 1. Store a memory — `POST /v1/experience`

Required fields: only **`scope`, `modality`, `content`**. Optional: `context`,
`observed_at`, `idempotency_key` (makes re-runs safe).

```bash
curl -sfS -X POST "$CORTEXDB_URL/v1/experience" \
  -H "Authorization: Bearer $CORTEXDB_API_KEY" \
  -H "X-Cortex-Actor: $CORTEXDB_ACTOR" \
  -H "Content-Type: application/json" \
  -d '{
    "scope": "org:acme/dept:eng/user:alice",
    "modality": "conversation",
    "content": {
      "kind": "message",
      "role": "user",
      "text": "Just got off a call with Priya at Acme."
    },
    "context": { "observed_at": "2026-05-15T10:42:00Z" },
    "idempotency_key": "alice-chat-001"
  }'
```

**Wait semantics:** omitting `?wait=` returns `202 captured` immediately (in WAL, not
yet indexed) with an `event_id` and a `lifecycle_stream` URL. `?wait=indexed` blocks
until BM25 + HNSW indexing is done and returns `200`. Accepted values: `accepted`
(alias of the default), `captured`, `indexed`, `consolidated`; any other value is
rejected with `422 INVALID_BODY`.

## 2. Recall — `POST /v1/recall` (the stratified pack)

```bash
curl -sfS -X POST "$CORTEXDB_URL/v1/recall" \
  -H "Authorization: Bearer $CORTEXDB_API_KEY" \
  -H "X-Cortex-Actor: $CORTEXDB_ACTOR" \
  -H "Content-Type: application/json" \
  -d '{
    "scope": "org:acme/dept:eng/user:alice",
    "view": "holistic",
    "query": "What did we decide about the Q3 launch?",
    "include": ["beliefs", "facts", "episodes"],
    "budgets": { "max_tokens": 4000 },
    "citation_mode": "inline_with_markers"
  }'
```

- `context_block` — ready-to-prompt text, held within `budgets.max_tokens`.
- `layers.events / facts / beliefs / episodes` — the structured layers.
- Oversized events come back as excerpts flagged `content._partial: true`; fetch the
  whole event with `GET /v1/events/{id}`.
- Views: `raw`, `granular` (alias `local`), `holistic`, `descend`, `lineage`,
  `structured`. `descend` rolls up a whole subtree (e.g. a scope root over many
  sub-scopes); `holistic` blends the layers with inherited context.

## 3. Grounded answer — `POST /v1/answer`

Recall + LLM in one call, citations included. The body field is **`question`**.

```bash
curl -sfS -X POST "$CORTEXDB_URL/v1/answer" \
  -H "Authorization: Bearer $CORTEXDB_API_KEY" \
  -H "X-Cortex-Actor: $CORTEXDB_ACTOR" \
  -H "Content-Type: application/json" \
  -d '{
    "scope": "org:acme/dept:eng/user:alice",
    "view": "holistic",
    "question": "Did Acme renew?",
    "temporal": { "natural": "last 30 days" }
  }'
```

`temporal.natural` filters by each memory's `observed_at`. On a bare self-hosted
server with no answer model configured, answering is unavailable (SDKs raise
`V1NotConfiguredError`, HTTP `503`) — `/v1/recall` still works without the answer
model.

## 4. Layer reads — `GET /v1/{events,facts,beliefs,...}`

```bash
# Events
curl -sfS "$CORTEXDB_URL/v1/events?scope=org:acme/dept:eng/user:alice&since=2026-04-01T00:00:00Z" \
  -H "Authorization: Bearer $CORTEXDB_API_KEY" \
  -H "X-Cortex-Actor: $CORTEXDB_ACTOR"

# Facts (with bi-temporal as_of)
curl -sfS "$CORTEXDB_URL/v1/facts?scope=org:acme/dept:eng&subject=ent_acme_corp&predicate=deal_stage&as_of=2026-04-15T00:00:00Z" \
  -H "Authorization: Bearer $CORTEXDB_API_KEY" \
  -H "X-Cortex-Actor: $CORTEXDB_ACTOR"

# Fact timeline (supersession chain)
curl -sfS "$CORTEXDB_URL/v1/facts/timeline?scope=org:acme/dept:eng&subject=ent_acme_corp&predicate=deal_stage" \
  -H "Authorization: Bearer $CORTEXDB_API_KEY" \
  -H "X-Cortex-Actor: $CORTEXDB_ACTOR"

# Beliefs + why
curl -sfS "$CORTEXDB_URL/v1/beliefs?scope=org:acme/dept:eng&about=ent_acme_corp" \
  -H "Authorization: Bearer $CORTEXDB_API_KEY" -H "X-Cortex-Actor: $CORTEXDB_ACTOR"
curl -sfS "$CORTEXDB_URL/v1/beliefs/why?belief_id=belief_01HX..." \
  -H "Authorization: Bearer $CORTEXDB_API_KEY" -H "X-Cortex-Actor: $CORTEXDB_ACTOR"
```

Facts appear roughly 5–30 s after a write (LLM-extracted); beliefs / understanding
rebuild async over minutes.

## 5. Forget / erasure

Targeted forget:

```bash
curl -sfS -X POST "$CORTEXDB_URL/v1/forget" \
  -H "Authorization: Bearer $CORTEXDB_API_KEY" \
  -H "X-Cortex-Actor: $CORTEXDB_ACTOR" \
  -H "Content-Type: application/json" \
  -d '{
    "scope": "org:acme/dept:eng/user:alice",
    "layers": ["beliefs"],
    "selector": { "predicate": "is_likely_to_renew" },
    "cascade": "derived_only",
    "audit_note": "User retracted speculation"
  }'
```

`cascade="derived_only"` keeps raw events and drops only derived layers;
`cascade="redact_events"` also redacts the raw events. Body accepts only `scope`,
`layers`, `selector`, `cascade`, `confirm_all`, `audit_note` (alias `reason`) and
`from_preview_id`.

GDPR-style whole-scope erasure — always preview first:

```bash
# Preview (returns a preview_id)
curl -sfS -X POST "$CORTEXDB_URL/v1/erasures/preview" \
  -H "Authorization: Bearer $CORTEXDB_API_KEY" \
  -H "X-Cortex-Actor: $CORTEXDB_ACTOR" \
  -H "Content-Type: application/json" \
  -d '{ "scope": "org:acme/user:alice", "confirm_all": true, "audit_note": "DSR #1234 — preview" }'

# Execute (202 on acceptance) — pass the preview_id back
curl -sfS -X POST "$CORTEXDB_URL/v1/erasures" \
  -H "Authorization: Bearer $CORTEXDB_API_KEY" \
  -H "X-Cortex-Actor: $CORTEXDB_ACTOR" \
  -H "Content-Type: application/json" \
  -d '{
    "scope": "org:acme/user:alice",
    "confirm_all": true,
    "from_preview_id": "ervw_01HX...",
    "idempotency_key": "erasure-dsr-1234",
    "audit_note": "DSR #1234"
  }'
```

## 6. Health / version (open, no key)

```bash
curl -sfS "$CORTEXDB_URL/v1/admin/health"   # {"status":"healthy","version":"v0.10.1"}
curl -sfS "$CORTEXDB_URL/v1/admin/version"  # version, crate_version, git_sha, capabilities
```
