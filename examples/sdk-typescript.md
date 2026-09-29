# TypeScript SDK examples

Source: https://cortexdb.ai/docs/quickstart/typescript (verified live 2026-09).
Package: `npm install cortexdbai` (the bare `cortexdb` npm name is a different,
unaffiliated package). Requires Node 18+.

## Three-line path via `V1Client.signup()`

```ts
import { V1Client } from "cortexdbai/v1";

const client = await V1Client.signup();
await client.experience(client.actor, {
  text: "Just got off a call with Priya at Acme. They upgraded to 200 seats.",
  observedAt: new Date().toISOString(),
  idempotencyKey: "alice-chat-001",
});
const pack = await client.recall(client.actor, {
  query: "What did we decide about Acme?",
  diagnostics: "none",
});
console.log(pack.context_block);
```

Persist the token across restarts:

```ts
process.env.CORTEX_TOKEN = client.bearer!;
process.env.CORTEX_ACTOR = client.actor;
```

## Explicit auth (permanent identities / managed instances)

```ts
import { V1Client } from "cortexdbai/v1";

const client = new V1Client({
  apiUrl: "https://api-v1.cortexdb.ai",   // or https://<tenant>.cortexdb.ai
  actor:  "user:alice@acme.com",
  bearer: process.env.CORTEX_TOKEN!,
  timeoutMs: 30_000,
});

const me = await client.whoami();
console.log(me.effective_capabilities);   // snake_case on the whoami response
```

## Capture / recall / answer signatures

```ts
// Capture
await client.experience(scope, {
  text:           "Acme upgraded to 200 seats.",
  role:           "user",                      // optional, default "user"
  observedAt:     new Date().toISOString(),
  idempotencyKey: "alice-chat-002",
  labels:         ["acme", "renewal"],
});

// Recall
const pack = await client.recall(scope, {
  view:        "holistic",   // raw | granular | holistic | descend | structured
  query:       "What did we decide?",
  include:     ["beliefs", "facts", "episodes"],
  budgets:     { max_tokens: 4000 },   // budgets use the wire (snake_case) names
  diagnostics: "none",                 // "summary" needs diagnostics.read (paid tier)
});

// Recall + LLM answer
const ans = await client.answer(scope, {
  question:    "Did Acme renew?",
  view:        "holistic",
  temporal:    { natural: "last 30 days" },
  diagnostics: "none",
});
```

On a self-hosted server with no answer model, `answer()` throws
`V1NotConfiguredError` (HTTP `503`); `recall()` still works.

## The `wait` parameter

Default is async — `experience()` returns `202 Accepted` once the WAL append
succeeds:

```ts
await client.experience(scope, { text: "...", observedAt: now, idempotencyKey: "k" },
  { wait: "indexed" });   // returns once BM25 + HNSW have the event
```

Accepted values: `"accepted"`, `"captured"`, `"indexed"`, `"consolidated"`
(30 s ceiling). Any other value is rejected by the server with `422 INVALID_BODY` —
use `"indexed"`.

## Inspecting derived layers

```ts
const facts    = await client.facts(scope);
const beliefs  = await client.beliefs(scope);
const concepts = await client.understanding(scope);
```

Facts populate within roughly 5–30 s of a write (enrichment required); beliefs and
understanding are eventually consistent. Facts are the recommended read-after-write
sanity check.
