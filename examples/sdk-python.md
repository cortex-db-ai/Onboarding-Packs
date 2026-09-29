# Python SDK examples

Source: https://cortexdb.ai/docs/quickstart/python (verified live 2026-09).
Package: `pip install cortexdbai` → import as `cortexdb.v1`. Python 3.10+.

## Signup (anonymous, no email/card)

```python
import requests
r = requests.post("https://api-v1.cortexdb.ai/v1/auth/signup", json={}).json()
TOKEN = r["token"]      # PASETO v4 bearer (7-day TTL on the free tier)
ACTOR = r["user_id"]    # e.g. "user:u_019e..."
SCOPE = r["scope"]      # your default scope path
print(r["expires_at"])  # ISO 8601; renew before this
```

## Open a client

```python
from cortexdb.v1 import V1Client

client = V1Client(
    api_url="https://api-v1.cortexdb.ai",
    actor=ACTOR,
    bearer=TOKEN,
)

print(client.whoami()["effective_capabilities"])
```

`api_url` defaults to `http://localhost:3141` — pass the cloud URL explicitly.
On a dev server started with `CORTEX_INSECURE_NO_AUTH=1`, skip the token:
`V1Client(api_url="http://localhost:3141", actor="user:local")` with
`SCOPE = "org:demo/user:local"`.

## Store a memory (experience write)

```python
from datetime import datetime, timezone

result = client.experience(
    scope=SCOPE,
    text="Just got off a call with Priya at Acme. They upgraded to 200 seats.",
    role="user",
    observed_at=datetime.now(timezone.utc).isoformat(),  # defaults to now
    idempotency_key="alice-chat-001",
)
print(result["event_id"])  # "evt_01HX..."
print(result["status"])    # "captured"
```

Returns `202 Accepted` once the WAL append lands. Use `wait="indexed"` to block up
to 30 s for BM25 + HNSW indexing; for longer waits poll
`GET /v1/lifecycle/stream?event_id=evt_…`.

## Recall a stratified pack

```python
pack = client.recall(
    scope=SCOPE,
    view="holistic",
    query="What did we decide about Acme's renewal?",
    include=["events", "beliefs", "facts", "episodes"],
    budgets={"max_tokens": 4000},
    diagnostics="none",   # free-tier tokens don't hold diagnostics.read
)

print(pack.get("context_block", ""))
for fact in pack["layers"].get("facts", []):
    print(fact["predicate"], "=", fact["object"]["value"])
```

Views: `raw`, `granular` (alias `local`), `holistic`, `descend`, `lineage`,
`structured`.

## Recall + LLM in one call (answer)

```python
answer = client.answer(
    scope=SCOPE,
    question="Did Acme renew?",
    view="holistic",
    temporal={"natural": "last 30 days"},
    diagnostics="none",
)

print(answer["answer"])
for c in answer["citations"]:
    print(f"  {c['marker']} → {c['layer']}:{c['id']}")
```

Without an answer model configured (bare self-hosted) this raises
`V1NotConfiguredError` (HTTP `503`) — `recall()` still works.

## Inspect why a belief exists

```python
beliefs = client.beliefs(scope=SCOPE)
if beliefs["items"]:
    top = beliefs["items"][0]
    trail = client.belief_why(top["id"])   # belief items key their id as `id`
    print(trail["narrative"])
```

Facts appear ~5–30 s after a write; use `client.facts(scope=…)` as a read-after-write
smoke test.

## Async variant

```python
from cortexdb.v1 import AsyncV1Client

async with AsyncV1Client(
    api_url="https://api-v1.cortexdb.ai",
    actor=ACTOR,
    bearer=TOKEN,
) as client:
    pack = await client.recall(scope=SCOPE, view="holistic", diagnostics="none")
```
