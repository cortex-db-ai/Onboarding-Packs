> **Pack track:** `01-self-host` in Onboarding-Packs — stand up a local CortexDB trial (Docker).

# CortexDB — Self-Hosted Trial Bundle

Everything needed to stand up a local [CortexDB](https://cortexdb.ai) instance for a
trial — a memory + knowledge layer with document/image/audio/video ingestion, source
connectors, a code-intelligence plane, and an MCP server for AI tools.

Designed to be followed by a **person** or handed to a **coding agent**.

## What's in this bundle

| File | What it is |
|---|---|
| **`CORTEXDB_SETUP_GUIDE.md`** | The step-by-step guide. Start here. |
| **`cortex.example.env`** | Env template for the CortexDB server container. Copy to `cortex.env` and fill in your key. |
| **`README.md`** | This file. |

Keep the two content files **together** — the guide references the env template.

## Prerequisites

- **Docker** (Docker Desktop or Engine) running.
- An **OpenAI API key** — powers the LLM (answers/reasoning), image/audio ingestion, and
  optionally the embeddings. *(Optional only if you use the fully-local fallback in the guide,
  where answer quality is lower.)*
- **Python 3.11+** — only needed for the connectors, SDK, or CLIs (not for the core server).
- Free disk: ~6 GB if embeddings run locally (Ollama image + model), ~2 GB if they run on the
  OpenAI API.

## One decision to make first: where embeddings run

Every stored memory is turned into a vector. You choose **once, before the first write**
(the choice is pinned to the data volume), between two equally supported options:

| | **Option A — local Ollama** | **Option B — OpenAI API** |
|---|---|---|
| What runs | One extra container + a 275 MB model on your machine | Nothing extra; same OpenAI key as the LLM |
| Cost / privacy | Free per call; text never leaves the box | Fractions of a cent per 1k tokens; text is sent to OpenAI |
| **Pick it if** | You want zero per-call cost or on-box vectors, and the machine can spare CPU/RAM | **Your machine has modest hardware** (laptop, no GPU, limited RAM/disk), or you want fewer moving parts |

The guide's §2 walks through both; the env template has a commented block for each.

## Quick start (do it yourself)

Open **`CORTEXDB_SETUP_GUIDE.md`** and follow it top to bottom. The short path to a working
instance is §1–§6:

1. Create the Docker network
2. Choose embeddings: **A** start Ollama + pull the model, or **B** nothing to start (OpenAI API)
3. Start Tika
4. `cp cortex.example.env cortex.env`, uncomment the embedding block for A **or** B, paste in
   your OpenAI key
5. Start the CortexDB container
6. Health check + a test write/read

Optional add-ons (do only what you need): §7 media, §8 connectors, §9 code plane &
enrichment, §10 MCP server, §11 Python SDK & CLI.

## Hand it to an AI agent

The guide has a **"Using this guide with an AI agent"** preamble at the top. To kick it off,
put both files where the agent can read them and give it this prompt:

```text
Follow CORTEXDB_SETUP_GUIDE.md to stand up CortexDB locally, step by step.
Docker is running. At section 2, ask me which embedding option I want (A: local
Ollama, or B: OpenAI API) before continuing; if I am unsure, recommend B on a
laptop or any machine without a GPU. When you reach the env step, create
cortex.env from cortex.example.env, uncomment the embedding block for my choice,
but STOP and ask me to paste the OpenAI key myself — do not put it in chat. Same
for any connector tokens. Run each section, verify with the checks in the guide,
and tell me if anything fails.
```

Works with any file-aware coding agent — Claude Code, Codex, Cursor, and others. In Claude
Code you can point at the file with `@CORTEXDB_SETUP_GUIDE.md`.

**The agent handles everything except the secrets and the one choice** — you pick the
embedding option and paste the OpenAI key and any connector tokens yourself; the agent should
never print or commit them.

## Security

- **Never share a filled-in `cortex.env`** — it contains a live OpenAI key. Share
  `cortex.example.env` (placeholders only). Add `cortex.env` to `.gitignore`.
- Use **throwaway/revocable tokens** for connectors, scoped to test data.
- Local-mode auth is a fixed placeholder token — **do not expose port `3141`** to the
  public internet.

## What you get once it's running

- **Write & recall** memories over an HTTP API (`:3141`), with a built-in Admin UI at `/`.
- **Media ingestion** — PDFs/Office (Tika), images (vision), audio/video (Whisper).
- **Connectors** — Slack, Jira, GitHub, Notion, and ~14 more sources.
- **Code plane** — index repositories and query cited code context.
- **MCP server** — expose CortexDB as a memory layer to Claude Code, Claude Desktop, Codex,
  Cursor, and other MCP clients.
- **SDK & CLI** — drive it from Python or the terminal.

See the guide for details, verification steps, and troubleshooting.

---

*Targets `cortexdb/cortexdb:v0.9.8`. Newer images ship often — the guide's Upgrading
section covers moving to a newer tag.*
