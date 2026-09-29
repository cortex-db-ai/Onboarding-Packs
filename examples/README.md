# CortexDB — worked examples (store, recall, answer, erase)

Copy-pasteable examples taken from the official docs at
[cortexdb.ai/docs](https://cortexdb.ai/docs) (REST reference + Python/TypeScript
quickstarts). Verified against the live docs surface — do not invent endpoints
anywhere else in this repo either.

| File | Language / surface | Covers |
|---|---|---|
| [`store-and-recall.md`](store-and-recall.md) | **REST (curl)** | signup, store an experience, recall views, grounded answer, layer reads, forget / GDPR erasure |
| [`sdk-python.md`](sdk-python.md) | **Python** (`pip install cortexdbai`) | signup, client, store, recall, answer, beliefs |
| [`sdk-typescript.md`](sdk-typescript.md) | **TypeScript** (`npm install cortexdbai`) | signup, client, store, recall, answer, layer reads, `wait` |

## The mental model in 20 seconds

- **Store** = `POST /v1/experience` — one immutable event per message/document/ticket. Only `scope`, `modality`, `content` are required.
- **Recall** = `POST /v1/recall` — returns a *stratified pack*: `context_block` (ready-to-prompt text) + `layers` (events, facts, beliefs, episodes) + provenance.
- **Answer** = `POST /v1/answer` — recall + LLM in one call, with citations. (Note: the body field is `question`, not `query`.)
- **Erase** = `POST /v1/forget` (+ `/v1/erasures/preview` → `/v1/erasures` for GDPR-style whole-scope erasure).
- `POST /v1/remember` is a **retired** route — it 404s. Never use it.

Every example assumes two env vars:

```bash
CORTEXDB_URL=https://api-v1.cortexdb.ai   # or your managed instance / localhost:3141
CORTEXDB_API_KEY=<your bearer token>      # free trial: from /v1/auth/signup
CORTEXDB_ACTOR=<user:... from signup>     # must match the token subject
CORTEXDB_SCOPE=<your default scope>
```

Get a free 7-day trial brain via [`../00-cloud/CLOUD.md`](../00-cloud/CLOUD.md) (Mode A).
