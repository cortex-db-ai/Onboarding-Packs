# CortexDB — Self-Hosted Trial Setup Guide

A step-by-step guide to stand up a local CortexDB instance with document, image, audio, and
video ingestion, plus source connectors (Slack, Jira, GitHub, Notion, and ~14 more).

This guide is written to be followed by a person **or** handed to a coding agent. Every
command is copy-pasteable. Placeholders look like `<THIS>` — replace them before running.

> **Version this targets:** server `cortexdb/cortexdb:v0.9.8` (latest as of 2026-08-22),
> `cortexdb-connectors` (latest on PyPI). Newer images ship often — check the
> [changelog](https://cortexdb.ai/changelog) and for a newer tag before you start
> (see [Upgrading](#12-upgrading)).

---

## Using this guide with an AI agent

This document is written to be executed by a coding agent (Claude Code, Codex, Cursor, etc.)
or a person. If you are an **agent** following it:

1. **Work through the sections in order** (§1 → §6 at minimum for a working instance). Run
   each command, then run that section's verify step before moving on.
2. **Never handle the user's secrets in chat.** At §4, create `cortex.env` from
   `cortex.example.env`, then **pause and ask the user to paste their OpenAI key into
   `cortex.env` themselves** (it appears on 5 to 7 lines — see §4). Do the same for connector
   tokens (§8). Do not print, echo, or commit these values.
3. **Assume the user has done the prerequisites** (Docker running). If a command fails
   because a prerequisite is missing, say so and stop — don't work around it.
4. **Report honestly.** If a verify step fails, show the actual output and the guide's
   troubleshooting row (§13) rather than declaring success.

A minimal working instance is §1–§6. §7 (media), §8 (connectors), §9 (code plane /
enrichment), §10 (MCP), and §11 (SDK/CLI) are optional add-ons — do only the ones the user
asks for.

---

## 0. What you're building

Four pieces on one Docker network (`cortexnet`):

| Component | What it is | Runs as |
|---|---|---|
| **cortexdb** | The database + API server (`:3141`) | Docker container |
| **ollama** | Local **embeddings** (`nomic-embed-text`) — **only if you choose embedding Option A** | Docker container |
| **tika** | Apache Tika — extracts text from documents | Docker container |
| **connectors** | `cortexdb-connectors` — pulls data from Slack/Jira/GitHub/Notion/etc. | Python on the host |

**Model split** (the recommended trial config):
- **Answers** — **OpenAI `gpt-5.6-terra`**, the best quality per dollar (about 2 to 4 cents per answer).
  `gpt-5.6-luna` is the budget option (about 0.2 to 0.4 cents); `gpt-5.6-sol` the premium option (4 to
  7 cents) where answer quality is the product. `gpt-6-astra` (11 to 18 cents) does not work yet: CortexDB
  sends `max_tokens`, which Astra rejects, so every answer fails. The model is set per deployment with
  `CORTEX_ANSWER_MODEL`; a per-request `answer_model` is accepted but not applied.
- **Entity extraction and enrichment** — OpenAI **`gpt-4o-mini`**, the cheapest reliable extraction
  model (about $0.40 per 1,000 events). The verifier stays on `gpt-4o`.
- **Embeddings** — **your choice, made once in [§2](#2-choose-where-embeddings-run)**. Both options
  are fully supported and behave identically from the API's point of view:
  - **Option A — local Ollama** (`nomic-embed-text`): free per call, vectors never leave the box;
    needs one more container and enough CPU/RAM to run the model.
  - **Option B — OpenAI API** (`text-embedding-3-small`): no extra container or local model, reuses
    the same OpenAI key as the LLM. **Choose B if your machine has modest hardware** (a laptop, no
    GPU, limited RAM or disk) or you want the fewest moving parts.

Images/audio/video ingestion also calls **OpenAI** (vision + Whisper); documents use Tika (no key).
So a single OpenAI key powers the LLM **and** media, and with Option B the embeddings too.

> **Zero-cost / fully-offline option:** with embedding Option A you can run the LLM locally on
> Ollama too (`qwen2.5:14b-instruct`) with no OpenAI key — answer quality is below gpt-5.6-terra, and
> the 14B model (~9 GB) realistically needs a GPU. The env template includes this fallback
> block, commented out.

**What it costs** (OpenAI list prices, September 2026). Question volume drives the cost, not corpus
size:

| Item | Cost |
|---|---|
| Load and enrich 10,000 events (one time) | about $4 |
| Each additional 1,000 events | about $0.40 |
| Each answered question, Terra | $0.02 to $0.04 |
| Each answered question, Luna | $0.002 to $0.004 |
| Each search without a generated answer | under $0.001 |
| 1,000 / 10,000 / 100,000 answers a month, Terra | $22 to $40 / $220 to $400 / $2,200 to $4,000 |

Assumes events of about 150 tokens and about 10,000 input tokens per answer; the answer range covers
reasoning tokens, which OpenAI bills as output. The built-in usage dashboard (v0.9.12+) reports actual
tokens and spend per role; `cortex.example.env` sets `CORTEX_MODEL_PRICES` so it prices the GPT-5.6
models correctly. Full detail: [Cost Planning](https://cortexdb.ai/docs/operations/cost-planning).

**Optional features you can turn on later** (off by default; each is one env toggle — see
[§9](#9-optional-features-code-plane--enrichment)):
- **Code Intelligence Plane** — ingest whole repos: symbol search, call graphs, impact
  analysis across 43+ languages ([§9a](#9a-code-intelligence-plane-repos--code)).
- **LLM enrichment** — extra fact/graph extraction on top of raw content; this guide runs
  content-only ([§9b](#9b-llm-enrichment-fact-augmentation)).
- **MCP server** — expose CortexDB as a memory layer to Claude Code / Desktop, Cursor, etc.
  (see [§10](#10-use-cortexdb-from-your-ai-tools-mcp-server)).

**Optional Python packages** (install only the ones you need — each has its own section):

| Package | Imports / command | Role | Section |
|---|---|---|---|
| `cortexdb-connectors` | `cortexdb-sync` | Ingest from Slack/Jira/GitHub/… | [§8](#8-connectors-ingest-from-your-tools) |
| `cortexdb-mcp` | `cortexdb-mcp` | MCP memory server for AI tools | [§10](#10-use-cortexdb-from-your-ai-tools-mcp-server) |
| `cortexdbai` | `import cortexdb` | Python SDK (`Cortex` / `AsyncCortex`) | [§11a](#11a-python-sdk--cortexdbai-imports-as-cortexdb) |
| `cortexdb-cli` | `cortexdb` | Terminal CLI + REPL | [§11b](#11b-terminal-cli--cortexdb-cortexdb-cli) |

**Prerequisites**
- Docker Desktop (or Docker Engine) running. Free disk: ~6 GB with embedding Option A (Ollama
  image + model), ~2 GB with Option B (CortexDB + Tika images only).
- Python 3.11+ on the host (needed for connectors, the SDK, or the CLIs).
- An **OpenAI API key** — powers the LLM (answer/reasoning), image/audio ingestion, and (with
  Option B) embeddings. *(Skip it only if you use the fully-local fallback, where answer
  quality is lower.)*

> This guide runs CortexDB in **enrichment-off / content-only mode** — it stores and indexes
> what you give it and runs extraction (Tika/vision/Whisper), but does not run the extra
> LLM-enrichment layer. This is the leanest way to see core behavior. It's a single env
> toggle to change later.

---

## 1. Create the network

```bash
docker network create cortexnet
```

*(If it already exists, Docker will say so — safe to ignore.)*

---

## 2. Choose where embeddings run

Every memory is embedded into a vector for recall. Pick **one** of the two options below;
both are fully supported and produce the same product behaviour. You will activate the
matching block in the env file in [§4](#4-create-your-env-file).

| | **Option A — local Ollama** | **Option B — OpenAI API** |
|---|---|---|
| Model | `nomic-embed-text` (768 dims) | `text-embedding-3-small` (1536 dims) |
| Extra pieces | One more container (`ollama`) + a 275 MB model download | None — same OpenAI key as the LLM |
| Cost | Free per call | Fractions of a cent per 1k tokens embedded |
| Privacy | Text to embed never leaves your machine | Text to embed is sent to OpenAI |
| Hardware | Needs CPU/RAM headroom to run the model; a GPU is not required but small machines will feel it | Nothing local |
| **Choose it when** | You want zero per-call cost or vectors must stay on the box, and the machine can spare the resources | **Your machine has modest hardware** (a laptop, no GPU, limited RAM or disk), or you want the fewest moving parts |

> **Decide once, before the first write.** CortexDB pins the embedding model and its dimensions
> to the data volume the first time it writes. Changing your mind later means the vector rebuild
> in [§12](#12-upgrading), not just an env edit. Picking neither is an
> error: v0.9.10+ refuses to boot without an embedding endpoint, and older images silently fall
> back to mock embeddings (recall "works" but returns nonsense).

### 2A. Option A — start Ollama and pull the embedding model

Skip this subsection entirely if you chose Option B.

```bash
docker run -d --name ollama --network cortexnet -p 11434:11434 \
  -v ollama-data:/root/.ollama --restart unless-stopped \
  ollama/ollama serve
```

Pull the embedding model (~275 MB, one time):

```bash
docker exec ollama ollama pull nomic-embed-text
```

Verify:

```bash
docker exec ollama ollama list
```

You should see `nomic-embed-text`.

> **Fully-local fallback only:** if you chose to run the LLM on Ollama too, also run
> `docker exec ollama ollama pull qwen2.5:14b-instruct` here (~9 GB; a GPU is strongly
> recommended — it's slow on CPU-only).

### 2B. Option B — OpenAI API embeddings

Nothing to start. The server calls `https://api.openai.com/v1/embeddings` directly with the
model `text-embedding-3-small` (1536 dims), using the same OpenAI key you already need for
the LLM. In [§4](#4-create-your-env-file) you will uncomment the `[B]` block in the env file;
its two key placeholders are filled by the same `sed` as the rest. (Two key lines because
v0.9.10+ reads `CORTEX_EMBEDDING_API_KEY` while older images read `OPENAI_API_KEY`; set both
and it works on any tag. Verified on v0.9.8 and v0.9.13.)

Two things to know:
- Embedding traffic is small (one call per stored memory or recall query) and cheap, but it
  **does** send the text of each memory to OpenAI. If that is not acceptable, use Option A.
- If the OpenAI endpoint is unreachable or the key is bad, writes cannot be vector-indexed and
  recall looks empty. The container log says so (`docker logs cortexdb`), and on v0.9.9+
  `GET /v1/ready` reports it under `checks.embeddings`.

---

## 3. Start Tika (document extraction)

```bash
docker run -d --name tika --network cortexnet --restart unless-stopped \
  apache/tika:latest-full
```

Tika listens on `:9998` **inside** the network only — CortexDB reaches it at
`http://tika:9998`. No host port and no API key needed.

---

## 4. Create your env file

Copy the template and fill in the placeholders:

```bash
cp cortex.example.env cortex.env
```

Then edit `cortex.env` in two places:

**(1) Activate the embedding option you chose in [§2](#2-choose-where-embeddings-run).** In the
`--- Embeddings ---` block, remove the leading `#` from the four `[A]` lines (Ollama) **or** the
six `[B]` lines (OpenAI). Exactly one block must be active.

**(2) Replace every `<YOUR_OPENAI_API_KEY>`** with your OpenAI key (`sk-...`). It appears on
five lines — the LLM roles (`CORTEX_ANSWER_API_KEY`, `CORTEX_VERIFIER_API_KEY`,
`CORTEX_ENTITY_API_KEY`) and media (`CORTEX_IMAGE_API_KEY`, `CORTEX_AUDIO_API_KEY`) — plus two
more, `CORTEX_EMBEDDING_API_KEY` and `OPENAI_API_KEY`, if you activated `[B]`:

```bash
# quick fill-in (macOS/Linux): replace all placeholders in one shot
sed -i 's|<YOUR_OPENAI_API_KEY>|sk-your-real-key|g' cortex.env
```

Everything else works as-is for a local trial. Prefer a different LLM provider, cheaper
model, or no cloud at all? See the commented blocks in the template.

Quick self-check before starting the server: `grep -c '^CORTEX_EMBEDDING_' cortex.env` should
print `8` for Option A or `9` for Option B (your block plus the four batching/timeout lines
further down). `4` means you activated neither block; `13` means both.

> **Security:** `cortex.env` holds a live key once filled in. Do **not** commit it or
> paste it into chat. Add it to `.gitignore`. The committed template is `cortex.example.env`.

---

## 5. Start CortexDB

```bash
docker run -d --name cortexdb --network cortexnet -p 3141:3141 \
  -v cortexdb-data-unified:/data --restart unless-stopped \
  --env-file cortex.env \
  cortexdb/cortexdb:v0.9.8 3141 /data
```

The trailing `3141 /data` are the server's arguments (port + data dir) — keep them.

> **Windows / Git-Bash users:** prefix `docker run` with `MSYS_NO_PATHCONV=1` so Git-Bash
> doesn't mangle the `/data` path, e.g. `MSYS_NO_PATHCONV=1 docker run ...`.

Give it ~10–20 seconds to boot, then check the containers are up (`cortexdb` + `tika`, plus
`ollama` if you chose Option A):

```bash
docker ps --format '{{.Names}}\t{{.Image}}\t{{.Status}}'
```

---

## 6. Verify it works

### 6a. Health check

```bash
curl -s http://127.0.0.1:3141/v1/health
```

Expected: `{"status":"healthy","version":"v0.9.8"}`

> **Use `127.0.0.1`, not `localhost`.** On Docker Desktop the IPv6 (`::1`) port proxy can
> wedge after container restarts — `localhost:3141` hangs while `127.0.0.1:3141` works.
> A Docker restart clears it. This is the single most common "it's broken" false alarm.

### 6b. Auth headers

Send **both** headers on every `/v1/*` **data** call — `Authorization: Bearer <token>`
authenticates (local mode uses the fixed token `noauth-local`) and `X-Cortex-Actor` says who
is acting. `/v1/health` and `/v1/ready` are open and need none.

```
-H "Authorization: Bearer noauth-local"
-H "X-Cortex-Actor: user:local"
```

> In this local posture either header alone is actually accepted (you only get `401` with
> *neither*), but always send both — that's what a secured deployment requires, so your calls
> stay portable.

> **This is a local-trial convenience, not production auth.** `noauth-local` is a fixed
> placeholder token for a machine only you can reach. For a real deployment, let the server
> generate and persist a proper API key on first boot (keyless boot) and use that instead —
> and never expose port `3141` to the public internet.

**The same four local values everywhere.** Every tool in this guide connects with the same
four settings — only the flag/env name changes. This is the whole cheat-sheet:

| | Base URL `http://127.0.0.1:3141` | Token `noauth-local` | Actor `user:local` | Scope `org:demo/user:demo` |
|---|---|---|---|---|
| **curl** (server API) | in the request URL | `-H "Authorization: Bearer …"` | `-H "X-Cortex-Actor: …"` | `"scope"` in the JSON body |
| **Connectors** (`cortexdb-sync`) | `--api-url` / `CORTEXDB_URL` | `--api-key` / `CORTEXDB_API_KEY` | `--actor` / `CORTEXDB_ACTOR` | `--scope-template` / `CORTEXDB_SCOPE_TEMPLATE` |
| **MCP** (`cortexdb-mcp`) | `CORTEXDB_URL` | `CORTEXDB_API_KEY` | `CORTEXDB_ACTOR` | `CORTEXDB_SCOPE` |
| **SDK** (`import cortexdb`) | `Cortex("http://127.0.0.1:3141")` | `bearer="…"` | `actor="…"` | 1st arg of each call |
| **CLI** (`cortexdb`) | `--endpoint` / `CORTEXDB_URL` | `--api-key` / `CORTEXDB_API_KEY` | `--actor` / `CORTEXDB_ACTOR` | `-S` / `--scope` / `CORTEXDB_SCOPE` |

> ⚠️ The connectors, the MCP server and the CLI default their base URL to **CortexDB Cloud**
> (`api-v1.cortexdb.ai`). The Python SDK defaults to `http://localhost:3141` (cortexdbai 0.11.0
> and newer; versions up to 0.10.0 used `3142`). Always set the base URL explicitly for a local trial.

### 6c. Write one memory

```bash
curl -sS -X POST "http://127.0.0.1:3141/v1/experience?wait=indexed" \
  -H "Authorization: Bearer noauth-local" \
  -H "X-Cortex-Actor: user:local" \
  -H "Content-Type: application/json" \
  --data '{
    "scope": "org:demo/user:demo",
    "modality": "observation",
    "content": { "kind": "message", "role": "user", "text": "The Q3 kickoff is on October 6th in Berlin." },
    "context": { "labels": ["setup-test"] },
    "idempotency_key": "setup-test-write-001"
  }'
```

`wait=indexed` blocks until the write is queryable, so the next step will find it.

> **Idempotency keys are global and expire ~24h after use.** A given `idempotency_key`
> dedups **across the whole store, not per scope** — reusing one (even in a different scope)
> silently drops the second write. Use a unique key per distinct write; omit it if you don't
> need dedup. Keys expire ~24 hours after first use.

### 6d. Read it back

```bash
curl -sS -X POST "http://127.0.0.1:3141/v1/recall" \
  -H "Authorization: Bearer noauth-local" \
  -H "X-Cortex-Actor: user:local" \
  -H "Content-Type: application/json" \
  --data '{
    "scope": "org:demo/user:demo",
    "query": "When and where is the Q3 kickoff?",
    "view": "holistic",
    "include": ["events","episodes","facts"],
    "diagnostics": "summary"
  }'
```

You should get back the kickoff fact. **CortexDB works.** ✅

> **Admin UI:** open `http://localhost:3141/` in a browser to browse what's stored.

> **Recall view tips:** `view=holistic` surfaces derived/extracted text;
> `view=raw` shows only the original event content; add `diagnostics=full` to populate
> the detailed `layers` breakdown.

> **Note on derived layers:** in the default content-only mode, the **Facts** and **Beliefs**
> layers stay empty (the boot log says as much: *"legacy fact pipeline not configured — facts+
> beliefs will stay empty"*). Events and vector recall work fully — which is why the read
> above returns the answer — but to populate the richer knowledge-graph layers, turn on
> **enrichment** ([§9b](#9b-llm-enrichment-fact-augmentation)) or set `CORTEX_V1_LAYERS_AUTO=1`.

### How CortexDB stores changes (read this once)

CortexDB is **append-only and temporal by design.** When a source record is edited or
deleted, CortexDB records a **new version** — it does **not** overwrite or erase the prior
state. So re-syncing an edited Jira issue or Slack message adds the new version alongside
the old one; recall returns the current view, but the history is retained on purpose.

This is expected behavior, not a bug: if you see an older value still present after an
edit, that's the temporal log working as intended. (Permanent removal is a separate,
explicit operation — e.g. `DELETE /v1/blobs/{id}` for a file.)

---

## 7. Ingest documents, images, audio, and video (media pipeline)

CortexDB ingests files via **blob references**: upload the bytes, then write an
experience that points at the blob. On write, the matching content processor runs and the
extracted text becomes searchable:

| File type | Processor | Needs cloud key? |
|---|---|---|
| Text / PDF / Office (docx, xlsx, …) | Apache Tika | No |
| Images | OpenAI vision | Yes (`CORTEX_IMAGE_API_KEY`) |
| Audio | OpenAI Whisper (ASR) | Yes (`CORTEX_AUDIO_API_KEY`) |
| Video | Keyframes (vision) + transcript (ASR) | Yes |

> You can supply your own transcript with an audio/video blob to **skip** re-transcription.

**1. Upload the file** to `/v1/blobs` — returns a `blob_id`. Max **32 MiB** per blob (larger
returns HTTP 413):

```bash
curl -s -X POST http://127.0.0.1:3141/v1/blobs \
  -H "Authorization: Bearer noauth-local" -H "X-Cortex-Actor: user:local" \
  -H "Content-Type: application/pdf" --data-binary @report.pdf
# -> {"blob_id":"blob_...","size_bytes":...,"content_type":"application/pdf","sha256":"..."}
```

**2. Write an experience** whose content references the blob (`kind: "blob_ref"`):

```bash
curl -s -X POST "http://127.0.0.1:3141/v1/experience?wait=indexed" \
  -H "Authorization: Bearer noauth-local" -H "X-Cortex-Actor: user:local" -H "Content-Type: application/json" \
  --data '{"scope":"org:demo/user:demo","modality":"document","content":{"kind":"blob_ref","blob_id":"blob_..."},"idempotency_key":"doc-1"}'
```

**3. Recall** with `view=holistic` — once extraction finishes, the text is searchable.

> ⏱️ **Extraction is asynchronous.** `wait=indexed` returns as soon as the event is stored —
> it does **not** wait for extraction. The content processor runs on a deferred scanner and
> can take up to ~60–90 s. Until it finishes, recall shows the raw `[blob:...]` reference;
> after, the extracted text appears. Watch it in the logs:

```bash
docker logs -f cortexdb
```

Look for `content processor dispatch ... content_only=true` then
`content processing complete ... derived_text_len=N` (verified: a test PDF surfaced its text
in recall ~90 s after the write).

> Documents work with **no cloud key**. Images, audio, and video require a valid
> `CORTEX_IMAGE_API_KEY` / `CORTEX_AUDIO_API_KEY` in your env (step 4).

To permanently remove a blob: `DELETE /v1/blobs/{blob_id}` (with the same auth headers).

---

## 8. Connectors (ingest from your tools)

Connectors run as a Python package **on the host** and push data into CortexDB. They are
**not** part of the Docker image.

**Supported sources.** Run `cortexdb-sync list` for the authoritative set and each one's
required config keys. As of connectors `0.2.20` the roster is:

| Slug | Source | Slug | Source |
|---|---|---|---|
| `slack` | Slack | `discord` | Discord |
| `jira` | Jira | `teams` | Microsoft Teams |
| `github` | GitHub | `google-workspace` | Google Workspace (Gmail + Calendar) |
| `gitlab` | GitLab | `salesforce` | Salesforce |
| `confluence` | Confluence | `hubspot` | HubSpot |
| `notion` | Notion | `zendesk` | Zendesk |
| `linear` | Linear | `intercom` | Intercom |
| `freshdesk` | Freshdesk | `servicenow` | ServiceNow |
| `tldv` | tl;dv | `pagerduty` | PagerDuty |

The config shape is the same for every source — a block keyed by the connector **slug**,
holding that source's token fields. Below we walk through **two examples in full** (Jira
and Slack); [§8d](#8d-adding-any-other-connector) shows how to configure any other source
from the same pattern.

### 8a. Install

```bash
python -m pip install --upgrade cortexdb-connectors
```

This installs the **`cortexdb-sync`** command-line tool, which you'll use to run syncs.
Confirm it's on your PATH:

```bash
cortexdb-sync --help      # subcommands: sync, watch, status, list, auth, serve
```

Some connectors need extras (install only what you use):
`slack_sdk` (Slack), `jira` (Jira), `PyMuPDF` (attachment handling).

```bash
python -m pip install slack_sdk jira PyMuPDF
```

### 8b. Configure credentials

Credentials can be supplied **two ways** (per `cortexdb-sync list`):
- **Environment variables** (the default) — e.g. `JIRA_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`,
  `SLACK_BOT_TOKEN`. `cortexdb-sync list` prints the exact variable names for each source.
- **A YAML file** via `--config` — auto-discovered at `./cortexdb-connectors.yaml` or
  `~/.cortexdb/connectors.yaml`. YAML values take precedence over env vars.

The YAML is keyed by connector **slug**. Field names are the connector's own (e.g. Jira's
secrets are `jira_url` / `jira_email` / `jira_api_token`; its option is `project_keys`) —
they mostly match the env-var names lowercased, but option fields drop the prefix. `cortexdb-sync
list` prints each connector's **required** env vars (→ required YAML fields); the two examples
below and the package docs cover the optional ones. **Each customer supplies their own tokens**
— use throwaway/sandbox tokens you
can revoke, and scope each connector to a small test project or channel so you don't pull an
entire company's data. Only include blocks for connectors you're actually using.

**Example 1 — Jira**

```yaml
# Get an API token: https://id.atlassian.com/manage-profile/security/api-tokens
jira:
  jira_url: https://<your-site>.atlassian.net
  jira_email: <your-atlassian-login-email>
  jira_api_token: <YOUR_JIRA_API_TOKEN>
  project_keys: [<TEST_PROJECT_KEY>]     # limit to ONE small test project
```

**Example 2 — Slack**

```yaml
# slack_bot_token = Bot User OAuth Token from the app's "OAuth & Permissions" page
slack:
  slack_bot_token: <YOUR_SLACK_BOT_TOKEN>
  # channels: [C0XXXXXXX]   # optional — else auto-discovers channels the bot is in
  # ingest_files: true      # optional — also pull file attachments (needs files:read)
```

The Slack connector's only required field is `slack_bot_token`; its options are `channels`,
`ingest_files`, and `file_types`. The **signing secret is *not* a sync field** — it's only
used by webhook mode (§8c, `serve`), read from the `SLACK_SIGNING_SECRET` env var.

> **Slack bot scopes** needed for full ingestion (including files): `channels:history`,
> `channels:read`, `groups:history`, `groups:read`, `users:read`, `reactions:read`,
> `files:read`, `chat:write`. Invite the bot to the channel you want ingested.

### 8c. Run a sync

> **⚠️ Point it at your local instance.** The connector defaults to CortexDB **Cloud**
> (`https://api-v1.cortexdb.ai`). For a local trial you **must** pass `--api-url` (or set
> `CORTEXDB_URL`) — otherwise your data goes to the cloud, not your container.

The CortexDB connection flags are **global** (they go *before* the subcommand). Set the
scope with the global **`--scope-template`**, also before the subcommand:

```bash
cortexdb-sync list                                    # connectors + their required env vars

cortexdb-sync \
  --api-url http://127.0.0.1:3141 \
  --api-key noauth-local \
  --actor  user:local \
  --config cortexdb-connectors.yaml \
  --scope-template "org:demo/user:demo" \
  sync jira
```

**How the connector resolves CortexDB creds** (per the CLI's own docs), highest priority first:
1. **CLI flags** — `--api-url`, `--api-key`, `--actor`, `--scope-template`
2. **Env vars** — `CORTEXDB_URL`, `CORTEXDB_API_KEY`, `CORTEXDB_ACTOR`, `CORTEXDB_SCOPE_TEMPLATE`
3. **`~/.cortexdb/state.json`** — written by `cortexdb init` (from the `cortexdb-cli` package) and read by `cortexdb-sync` **and** the `cortexdb` CLI, so those two can share one identity. Point it at your local instance (bare `cortexdb init` does an anonymous *cloud* signup — not what you want locally):

```bash
cortexdb init --endpoint http://127.0.0.1:3141 --api-key noauth-local \
  --actor user:local --scope org:demo/user:demo
```

> The **MCP server** (`cortexdb-mcp` 0.6.0) does **not** read that file — it uses its own
> config path + the `CORTEXDB_*` env vars from [§10](#10-use-cortexdb-from-your-ai-tools-mcp-server).

> **Scope is set with `--scope-template` (or the `CORTEXDB_SCOPE_TEMPLATE` env var)** — that's
> the documented mechanism, and it accepts a `{source}` placeholder. The `sync <src> --scope …`
> subcommand flag exists but is only really used with *flat* scopes; don't pass a hierarchical
> `org:x/user:y` to it.

Confirm it's aimed at the right place before syncing:

```bash
cortexdb-sync --api-url http://127.0.0.1:3141 --api-key noauth-local auth   # prints resolved creds (redacted)
```

**Three run modes:**

| Command | Behavior |
|---|---|
| `sync <source>` | One-shot poll — sync once and exit. Add `--since <ts>` for incremental. |
| `watch <source>` | Poll forever, sleeping between cycles. |
| `serve --host 0.0.0.0 --port 8088` | Webhook receiver for real-time create/update/delete — point the source's webhooks at it. |

Add **`--wait-derivation`** to a `sync` to block until derived layers (facts/concepts) catch
up — otherwise events + embeddings are written synchronously, but belief/episode/concept
synthesis runs on a ~30s scheduler tick and lags slightly behind.

> `--scope-template` also accepts a `{source}` placeholder — e.g. `"org:demo/source:{source}"`
> derives the scope from the connector slug.

**Verify it landed.** A **recall** query is the reliable check (it found real synced Jira
issues in testing):

```bash
curl -s -X POST "http://127.0.0.1:3141/v1/recall" \
  -H "Authorization: Bearer noauth-local" -H "X-Cortex-Actor: user:local" -H "Content-Type: application/json" \
  --data '{"scope":"org:demo/user:demo","query":"<something you know is in that source>","view":"holistic","include":["events"],"diagnostics":"summary"}'
```

You can also list raw events with `GET /v1/events?scope=<scope>` (`{items, has_more}`), but
note exact-scope listing may not show connector data if the connector wrote under a derived
child scope — recall (holistic) is the surer confirmation.

### 8d. Adding any other connector

Every connector follows the **same three-part recipe** — the two examples above are just
this recipe filled in. To wire up GitHub, Confluence, Google Workspace, Notion, Freshdesk,
tl;dv, or any newer source:

1. **Find the exact field names.** `cortexdb-sync list` prints each connector's **required**
   env vars — lowercase them (dropping the connector prefix for options) to get the YAML
   field names. Optional fields are in the package README / connector docs. *(Note: `sync
   <source> --help` shows only the generic sync flags — `--since`, `--scope`,
   `--wait-derivation` — not per-connector config.)*
   ```bash
   cortexdb-sync list                 # connectors + their required env vars
   ```

2. **Add a YAML block** keyed by the source name, filling in those fields. The shape is
   always the same — a site/domain (if the source is self-hostable or multi-tenant) plus a
   **token**, and optionally a **scope** field to limit what's pulled:
   ```yaml
   <source>:
     <source>_domain: <your-host>        # only if the source has one (e.g. Freshdesk, self-hosted)
     <source>_api_token: <YOUR_TOKEN>    # exact key name comes from step 1
     # optional scoping — e.g. specific repos / spaces / channels / projects
   ```
   *For example:* Freshdesk needs `freshdesk_domain` + `freshdesk_api_key`; tl;dv needs
   just `tldv_api_key`. Names vary per source — take them from step 1, not from memory.

3. **Get the token** from that product's developer/API settings, then **scope it small**
   (one repo, one space, one project) and make sure it's **revocable**. Common locations:
   - **GitHub:** Settings → Developer settings → Personal access tokens (fine-grained; grant only the repos you're testing).
   - **Confluence:** same Atlassian API token as Jira (`id.atlassian.com` → Security → API tokens).
   - **Google Workspace:** OAuth client / service-account credentials from Google Cloud Console.
   - **Notion:** an internal integration token from notion.so/my-integrations, then share the specific pages/databases with it.
   - **Freshdesk:** Profile Settings → Your API Key (enable API access in Agent Settings first).
   - **tl;dv:** workspace Settings → Developers/API.

4. **Run it and verify** exactly as in §8c — sync the one connector, then recall a fact you
   know lives in that source.

> **Rule of thumb:** if you can name the source, its token, and one thing to scope it to,
> you have everything a connector block needs. When unsure of a required field, `cortexdb-sync
> list` is the source of truth — it always matches the installed version.

---

## 9. Optional features: Code Plane & enrichment

Two capabilities are **off by default** and turned on the same way: uncomment their block in
`cortex.env`, then recreate the container. Both are marked in the env template so you just
delete the leading `#`.

### 9.0. How to apply any env change (do this after uncommenting either block)

Recreating the container **keeps your data** — it lives in the `cortexdb-data-unified`
volume, not the container:

```bash
docker rm -f cortexdb
MSYS_NO_PATHCONV=1 docker run -d --name cortexdb --network cortexnet -p 3141:3141 \
  -v cortexdb-data-unified:/data --restart unless-stopped --env-file cortex.env \
  cortexdb/cortexdb:v0.9.8 3141 /data
```

---

### 9a. Code Intelligence Plane (repos & code)

Ingest whole repositories and query them: cited code context, symbol search/resolve,
caller/callee and reverse-impact analysis, symbol history, and graph exports — tree-sitter
across many languages, optional SCIP tier. Off by default. **Reference docs:**
<https://cortexdb.ai/v2/code-plane/> (verified working on v0.9.8 in this guide's testing).

**Step 1 — enable & mount the repo.** Uncomment `CORTEX_CODE_PLANE=1` in `cortex.env`, and
**mount the repository into the container** (the plane indexes a path *inside* the
container, not a host path). Recreate the container with an extra `-v`:

```bash
docker rm -f cortexdb
MSYS_NO_PATHCONV=1 docker run -d --name cortexdb --network cortexnet -p 3141:3141 \
  -v cortexdb-data-unified:/data --restart unless-stopped --env-file cortex.env \
  -v /path/to/your/repo:/repos/shop:ro \
  cortexdb/cortexdb:v0.9.8 3141 /data
```

**Step 2 — register the checkout** (`path` is the **container** mount point):

```bash
curl -s -X POST http://127.0.0.1:3141/v1/code/repos \
  -H "Authorization: Bearer noauth-local" -H "X-Cortex-Actor: user:local" \
  -H "Content-Type: application/json" \
  --data '{"name":"shop","path":"/repos/shop"}'
```

Returns `201` with parse stats (`files`, `definitions`, `predicate_counts.calls/defines`, …)
— confirmation it indexed your code.

**Step 3 — query for cited context:**

```bash
curl -s -X POST http://127.0.0.1:3141/v1/code/context \
  -H "Authorization: Bearer noauth-local" -H "X-Cortex-Actor: user:local" \
  -H "Content-Type: application/json" \
  --data '{"repo":"shop","task":"How is the checkout total calculated?","token_budget":800}'
```

Returns snippets with citations like `shop:orders.py@<hash>#L1-L10`, a `reason` per hit
(`symbol-anchor`, `caller`, `route`, `import`, `test`), token accounting, and uncertainty
warnings. Beyond these two, the plane exposes ~21 `/v1/code/*` routes (symbol search/resolve,
callers/callees, reverse impact, change-testing, symbol history, graph export in several
formats) — see the reference docs for exact paths.

> **Notes from testing:** (1) The `/v1/code/*` routes are **not listed in the server's
> OpenAPI**, but they exist — when the plane is off they return `503 CODE_PLANE_DISABLED`,
> which is the quickest way to check the flag took. (2) The GitHub connector (§8) emits
> **code anchors** that complement this plane. (3) The reference docs are labelled v0.9.6;
> the `repos` + `context` flow above was confirmed on v0.9.8.

### 9b. LLM enrichment (fact augmentation)

By default this guide runs **content-only** mode: CortexDB stores and indexes what you give
it, runs extraction (Tika/vision/Whisper), and derives facts — but does **not** run the
extra LLM pass ("fact augmentation") that mines additional entities, relationships, triples,
and summaries from your content and indexes them as searchable facts.

**Enable** (verified end-to-end on v0.9.8 with OpenAI `gpt-4o-mini`): fact augmentation needs
its **own** enrichment LLM endpoint — it does *not* reuse the answer lane's key. Uncomment
all of these in `cortex.env`, then run §9.0:

```
CORTEX_ENRICHMENT_MODEL=gpt-4o-mini
CORTEX_ENRICHMENT_URL=https://api.openai.com/v1
CORTEX_ENRICHMENT_API_KEY=<YOUR_OPENAI_API_KEY>
CORTEX_ENRICHMENT_DELAY_SECONDS=5
CORTEX_ENRICHMENT_CONCURRENCY=2
```

`DELAY_SECONDS` is how long after a write enrichment waits; `CONCURRENCY` is parallel enrichment jobs.
Keep the values bare in the env file (Docker's `--env-file` keeps a trailing `# comment` as part of the
value).

On boot, success looks like:
`Enrichment LLM router enabled for fact augmentation model=gpt-4o-mini` and
`... graph enrichment fact_augmentation=true`. If you set only the model, you'll instead see
`CORTEX_ENRICHMENT_MODEL set but no endpoint-compatible API key available — fact augmentation
disabled` — that means the URL/key are missing.

> **Cost/latency:** enrichment calls the LLM for every ingested item, so it uses OpenAI quota
> and adds latency: about $0.40 per 1,000 events with `gpt-4o-mini`, about $4 for 10,000. On the fully-local Qwen fallback it's slow on CPU-only hardware — use a
> GPU or keep enrichment off there.

**Verify:** write a fact-rich sentence, wait ~20s (the deferred delay + a scheduler tick),
then recall. In testing, *"Acme Corp acquired Beta Labs in March 2025 for $50 million. Jane
Doe, Acme's CFO, led the deal."* produced a recall **Timeline** with augmented facts
("Jane Doe led the acquisition of Beta Labs", "acquisition cost $50 million") that
content-only mode does not derive. The logs show `enrichment job complete ... entities=3
edges=3 facts=2 triples=3`.

---

## 10. Use CortexDB from your AI tools (MCP server)

CortexDB ships a **Model Context Protocol server** (`cortexdb-mcp`, a separate package) that
exposes CortexDB as a long-term **memory layer** to any MCP-compatible client — Claude Code,
Claude Desktop, Codex, Cursor, Windsurf, VS Code Copilot, and others. This is the piece to
wire up if you want an agent to read and write CortexDB directly.

### 10a. Install

```bash
python -m pip install --upgrade cortexdb-mcp
cortexdb-mcp --help        # runs over stdio transport
```

### 10b. Point it at your local instance

The MCP server, like the connectors, **defaults to CortexDB Cloud** — and if no
`CORTEXDB_API_KEY` is set it will *anonymously sign up to the cloud on first launch*. For a
local trial, always set these environment variables so it targets your container:

| Env var | Local-trial value | Notes |
|---|---|---|
| `CORTEXDB_URL` | `http://127.0.0.1:3141` | **Required** — else it uses the cloud. |
| `CORTEXDB_API_KEY` | `noauth-local` | **Required** — else it auto-signs-up to the cloud. |
| `CORTEXDB_ACTOR` | `user:local` | Sent as `X-Cortex-Actor`. |
| `CORTEXDB_SCOPE` | `org:demo/user:demo` | Which scope memories read/write. |
| `CORTEXDB_VIEW` | `holistic` | Default recall view. |
| `CORTEXDB_TENANT_ID` / `CORTEXDB_TIMEOUT` | *(optional)* | Tenant id; HTTP timeout secs. |

### 10c. Register it with an MCP client

Add a server entry to the client's MCP config (e.g. Claude Desktop's
`claude_desktop_config.json`, or a project `.mcp.json` for Claude Code):

```json
{
  "mcpServers": {
    "cortexdb": {
      "command": "cortexdb-mcp",
      "env": {
        "CORTEXDB_URL": "http://127.0.0.1:3141",
        "CORTEXDB_API_KEY": "noauth-local",
        "CORTEXDB_ACTOR": "user:local",
        "CORTEXDB_SCOPE": "org:demo/user:demo",
        "CORTEXDB_VIEW": "holistic"
      }
    }
  }
}
```

Restart the client; the CortexDB tools then appear to the agent.

### 10d. Tools it exposes

`cortexdb-mcp` 0.6.0 exposes **20 tools** (verified via a live `list_tools`). The core set:

| Tool | Does |
|---|---|
| `memory_store` | Write a memory (maps to `/v1/experience`). |
| `memory_search` · `advanced_search` | Semantic search / filtered search. |
| `get_context` | Fetch a ready-to-use context block for a query. |
| `memory_list` · `memory_get` · `memory_status` | List / fetch one / check write status. |
| `memory_forget` · `memory_delete` · `memory_bulk_delete` | Forget / delete memories. |
| `entity_list` · `entity_get` · `entity_edges` · `entity_link` | Explore & link the knowledge graph. |
| `list_conflicts` · `resolve_conflict` · `claim_history` | Conflicts and bi-temporal history. |
| `health_check` · `get_usage` · `get_insights` | Server health, usage, and generated insights. |

> **Note:** the `*_forget` / `*_delete` tools can redact data — treat them with the same care
> as any delete. On an append-only store they record a forget/tombstone rather than rewriting
> history. Entity/conflict tools are most useful once **enrichment** (§9b) is on, which is what
> populates the graph/facts they read.

---

## 11. Scripting CortexDB (Python SDK & `cortexdb` CLI)

Two more official packages let you drive CortexDB from code or a terminal instead of raw
`curl`. Both **default to CortexDB Cloud**, so point them at your local instance explicitly.

### 11a. Python SDK — `cortexdbai` (imports as `cortexdb`)

```bash
python -m pip install --upgrade cortexdbai
```

```python
from cortexdb import Cortex          # AsyncCortex is the asyncio equivalent

# NOTE: the SDK's default api_url is http://localhost:3141 (cortexdbai 0.11.0+; 3142 in older
# versions). Pass the URL explicitly anyway so the target is never ambiguous.
cx = Cortex("http://127.0.0.1:3141", actor="user:local", bearer="noauth-local")

# Write (text is first-class; wait="indexed" blocks until queryable)
cx.experience(
    "org:demo/user:demo",
    text="The Q3 kickoff is on October 6th in Berlin.",
    labels=["setup-test"],
    idempotency_key="sdk-write-001",
    wait="indexed",
)

# Recall, and a grounded answer with citations
ctx = cx.recall("org:demo/user:demo", query="When and where is the Q3 kickoff?", view="holistic")
ans = cx.answer("org:demo/user:demo", "When and where is the kickoff?", cite_sources=True)

# Ingest a file: upload the bytes, then reference the blob
blob = cx.upload_blob(open("report.pdf", "rb").read(), content_type="application/pdf")
cx.experience("org:demo/user:demo", blob_id=blob["blob_id"], wait="indexed")

cx.close()
```

Handy methods: `experience` / `experience_bulk`, `recall`, `answer`, `events`, `facts`,
`beliefs`, `episodes`, `forget`, `upload_blob`, `compose`, `whoami`, `write_status`.
Failures raise typed `V1Error` subclasses (`V1AuthError`, `V1RateLimitError`,
`V1TimeoutError`, …). For dev-local you may omit `bearer`.

### 11b. Terminal CLI — `cortexdb` (`cortexdb-cli`)

```bash
python -m pip install --upgrade cortexdb-cli
```

Global flags go before the subcommand (`--endpoint` defaults to the cloud):

```bash
# Store, then recall — pointed at your local instance
cortexdb --endpoint http://127.0.0.1:3141 --actor user:local --api-key noauth-local \
  experience -S org:demo/user:demo "The Q3 kickoff is on October 6th in Berlin."

cortexdb --endpoint http://127.0.0.1:3141 --api-key noauth-local \
  recall -S org:demo/user:demo "When and where is the Q3 kickoff?"
```

To avoid repeating flags, run `cortexdb init` once (saves your identity to
`~/.cortexdb/state.json` — pass `--endpoint http://127.0.0.1:3141 --api-key noauth-local`
for a local target, since bare `init` does an anonymous cloud signup), or set `CORTEXDB_URL`
/ `CORTEXDB_API_KEY` / `CORTEXDB_ACTOR` / `CORTEXDB_SCOPE`. Running `cortexdb` with no command
opens an interactive **REPL**. Nice touches: `recall` accepts `--temporal "last 30 days"`
(natural-language windows) and view modes `holistic` (scope + parents) / `descend`
(scope + children) / `granular` (exact scope only).

Beyond `experience`/`recall`/`answer`/`search`, the CLI covers the derived layers and admin
surface: `facts`, `beliefs`, `episodes`, `concepts`, `entities`, `claims`, `conflicts`,
`compose`, `export` / `import`, `forget`, `scopes`, `auth`, `policy`, `admin`, `config`.

---

## 12. Upgrading

New server images ship frequently. To move to a newer tag safely:

```bash
# 1. Check for and pull a newer tag (replace X.Y.Z)
docker manifest inspect cortexdb/cortexdb:vX.Y.Z && docker pull cortexdb/cortexdb:vX.Y.Z

# 2. Back up the data volume first
MSYS_NO_PATHCONV=1 docker run --rm -v cortexdb-data-unified:/data:ro \
  -v "$PWD/backups":/b alpine sh -c "tar czf /b/pre-vX.Y.Z.tar.gz -C /data ."

# 3. Swap the container (keep the same volume + env file)
docker stop cortexdb && docker rename cortexdb cortexdb_prev
MSYS_NO_PATHCONV=1 docker run -d --name cortexdb --network cortexnet -p 3141:3141 \
  -v cortexdb-data-unified:/data --restart unless-stopped --env-file cortex.env \
  cortexdb/cortexdb:vX.Y.Z 3141 /data

# 4. Verify: /v1/health reports vX.Y.Z, and a pre-upgrade record still recalls.
```

Connectors: `python -m pip install --upgrade cortexdb-connectors`.

**Switching embedding option after the first write (A ↔ B).** The model and its dimensions are
pinned to the data volume, so a plain env edit is refused at boot. On **v0.9.12 or newer** the
supported path is a one-shot rebuild: back up (step 2 above), edit the embedding block in
`cortex.env`, then start the server **once** with two extra flags,
`-e CORTEX_EMBEDDING_ALLOW_REPIN=1 -e CORTEX_EMBEDDING_REBUILD_VECTORS=1`, and afterwards run
`POST /v1/admin/index-audit` with `{"scope":"<scope>","repair":true,"vectors":true}` for each
scope to refill the vectors (each memory is re-embedded, which costs OpenAI calls under
Option B). Restart without the two flags when done. On **older images** there is no rebuild:
export what you need, start a fresh data volume with the new option, and re-ingest.

> **Downgrades are not always possible** — newer versions may add on-disk structures older
> servers can't open (they fail closed, without harming data). Always back up before upgrading.

---

## 13. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `curl localhost:3141` hangs | Use `127.0.0.1` instead (Docker Desktop IPv6 proxy wedge). Restart Docker to clear. |
| `401 Unauthorized` | You sent **neither** auth header. Add `Authorization: Bearer noauth-local` and `X-Cortex-Actor: user:local` (either alone works locally, but send both). |
| Health check fails / container restarting | `docker logs cortexdb` — usually a bad env value, no embedding block activated (v0.9.10+ refuses to boot), or (Option A) Ollama not reachable. |
| Recall returns nothing right after a write | Add `?wait=indexed` to the write, or wait a moment before recall. |
| `/v1/answer` errors or returns empty | Missing/invalid OpenAI key, or a `429` rate limit. Check the LLM `*_API_KEY` values; lower `CORTEX_LLM_MAX_IN_FLIGHT` on 429s. |
| Image/audio ingestion produces no text | Missing/invalid OpenAI key in `cortex.env`. Documents (Tika) don't need one. |
| Embeddings fail but LLM works (or vice-versa) | They're separate lanes — embeddings = Ollama (Option A) or OpenAI `text-embedding-3-small` (Option B); LLM = OpenAI. Check the lane that's failing: for B, `CORTEX_EMBEDDING_API_KEY` must be a real key; for A, see the next row. |
| `413` on blob upload | File exceeds the 32 MiB blob cap. Split or shrink it. |
| Ollama errors / embeddings fail (Option A) | Confirm `docker exec ollama ollama list` shows `nomic-embed-text` (plus `qwen2.5:14b-instruct` only if you use the local-LLM fallback); re-pull if missing. |
| Boot log says the embedding model/dims don't match the data volume | You changed embedding option after the first write. Either go back to the original option, or do the vector rebuild in §12. |
| Enrichment on but no augmented facts | Needs `CORTEX_ENRICHMENT_MODEL` **and** `CORTEX_ENRICHMENT_URL` + `CORTEX_ENRICHMENT_API_KEY` (§9b). Boot log `fact_augmentation=false` / "no endpoint-compatible API key" means the URL/key are missing. |
| `/v1/code/*` returns `503 CODE_PLANE_DISABLED` | Plane off — uncomment `CORTEX_CODE_PLANE=1` and recreate (§9a). |
| `/v1/code/repos` register fails / can't find path | `path` must be the repo's mount point **inside** the container (e.g. `/repos/shop` from `-v /host/repo:/repos/shop`), not the host path. |
| `422 Unprocessable` on write | Strict envelope validation — an unknown/misspelled field in the write body was rejected. |
| `409 IDEMPOTENCY_CONFLICT` | You reused an `idempotency_key`. Keys are global and last ~24h — use a fresh one per distinct write. |
| Old value still shows after an edit | Expected — CortexDB is append-only (§6, "How CortexDB stores changes"). Recall returns the current view; history is retained by design. |
| `cortexdb-sync: command not found` | The connectors package isn't installed or its scripts dir isn't on PATH — `python -m pip install --upgrade cortexdb-connectors` (§8a). |
| Sync reports success but nothing shows locally | You didn't pass `--api-url` — the connector defaulted to CortexDB **Cloud** (`api-v1.cortexdb.ai`). Add `--api-url http://127.0.0.1:3141` (§8c); run `cortexdb-sync ... auth` to confirm the target. |
| `cortexdb-sync sync … ValueError: Invalid name '…lock'` | You passed the scope via the subcommand flag (`sync <src> --scope org:x/user:y`). Set it with the **global** `--scope-template "org:x/user:y"` (before the subcommand) or `CORTEXDB_SCOPE` instead (§8c). |
| Event is there but its facts/concepts aren't yet | Derived layers synthesize on a ~30s tick. Wait, or add `--wait-derivation` to the sync. |
| MCP agent's memories don't appear locally | `cortexdb-mcp` defaulted to the cloud. Set `CORTEXDB_URL=http://127.0.0.1:3141` **and** `CORTEXDB_API_KEY=noauth-local` in the MCP server's `env` (§10b) — without the key it anonymously signs up to the cloud. |

---

## Appendix A — API surface at a glance

All routes require the two auth headers. Handy for driving CortexDB from code/an agent:

| Route | Purpose |
|---|---|
| `POST /v1/experience?wait=indexed` | Write a memory (observation, message, or a `triple` for deterministic facts). |
| `GET /v1/experience/status` | Check write status by idempotency key or event ID. |
| `GET /v1/events?scope=<scope>` | List raw ingested events in a scope — `{items, has_more}`. Handy to verify a sync. |
| `POST /v1/recall` | Retrieve — `view=holistic\|raw`, `include`, `diagnostics`, metadata `filters`. |
| `POST /v1/answer` | Grounded answer over memories; `cite_sources: true` for citations, `skip_answer_llm` for context-only preview. |
| `POST /v1/blobs` · `DELETE /v1/blobs/{id}` | Upload a file for extraction / permanently remove it (32 MiB cap). |
| `POST /v1/code/repos` · `POST /v1/code/context` | Register a repo / query cited code context (needs `CORTEX_CODE_PLANE=1`; ~21 `/v1/code/*` routes, not in OpenAPI) — [§9a](#9a-code-intelligence-plane-repos--code). |
| `POST /v1/admin/scopes/migrate` | Copy/move an entire scope. |
| `GET /v1/health` | Liveness + version. |
| `GET /` | Admin UI (metrics, logs, feature toggles, settings, API reference). |

**Notable capabilities:** temporal queries on independent axes (`as_of_valid`,
`as_of_recorded`); metadata filters (labels, intent, modality, caller, observed_actor);
`triple` writes canonicalized against the ontology at ingest.

> Exact request bodies evolve per release — the Admin UI links the API reference bundled
> with your server version. Treat this table as a map, not a frozen contract.

---

## Appendix B — quick command reference

```bash
# Status of the whole stack
docker ps --format '{{.Names}}\t{{.Image}}\t{{.Status}}'

# Server logs (follow)
docker logs -f cortexdb

# Health
curl -s http://127.0.0.1:3141/v1/health

# Stop / start everything (drop `ollama` if you chose embedding Option B)
docker stop cortexdb tika ollama
docker start ollama tika cortexdb

# Full teardown (KEEPS data volume)
docker rm -f cortexdb tika ollama

# Nuke data too (irreversible; ollama-data only exists with Option A)
docker volume rm cortexdb-data-unified ollama-data
```

**Security checklist before sharing this setup**
- Never share a filled-in `cortex.env` — it contains a live OpenAI key. Share `cortex.example.env`.
- Each customer uses their **own** OpenAI + connector tokens, scoped to test data, and revocable.
- Local mode auth is a fixed placeholder token — do **not** expose port `3141` to the public internet.
