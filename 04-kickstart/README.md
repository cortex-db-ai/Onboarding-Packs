# 04 — Kickstart pack (the "Helper Agent" docs)

**The brief version of the docs.** For a serious team with good enterprise data that
wants to get running fast — setup first, then the bare-basic use cases, with links to
the full documentation for depth. Everything here is agent-friendly: hand the whole
folder to a coding agent and it has what it needs.

| File | What it answers |
|---|---|
| [`SETUP.md`](SETUP.md) | *What do I need to define before my first write?* — the five decisions, then minimal commands to prove they work. |
| [`USE-CASES.md`](USE-CASES.md) | *What do I actually do with it?* — the basic enterprise patterns: support memory, cross-source search, per-user memory, compliance time-travel, erasure. |
| [`COSTS.md`](COSTS.md) | *What will it cost me?* — hosting/CPU by data size with cloud-provider anchors, then embedding, enrichment, and answer costs. |

## Who this is for

- An **enterprise team** onboarding real data (tickets, chat, docs, CRM) that wants a
  checklist, not a manual.
- A **coding agent** told "set CortexDB up for us" — read `SETUP.md`, execute, then
  pick the use cases from `USE-CASES.md` that match the team's workload.

## How it fits with the rest of this repo

- Need **keys / a hosted brain** first? → [`../00-cloud/`](../00-cloud/) (free trial or managed instance) or [`../01-self-host/`](../01-self-host/) (Docker).
- Want **copy-paste API examples** in curl / Python / TypeScript? → [`../examples/`](../examples/).
- Wiring memory **into an app repo**? → [`../02-app-in-repo/`](../02-app-in-repo/).
- Attaching an **IDE / chat tool** to a brain? → [`../03-harness-attach/`](../03-harness-attach/).

## Standing rules (agents, read this)

1. **Recall → act → write.** Look things up before inventing them.
2. **Never invent endpoints.** Everything you may call is in the docs:
   <https://cortexdb.ai/docs> — task router at <https://cortexdb.ai/llms.txt>.
3. `POST /v1/remember` is retired — it 404s. Writes are `POST /v1/experience`.
4. **Never print or commit tokens.** Keys go in a gitignored `.env`.
5. Install the SDK as `cortexdbai` (Python: `pip install cortexdbai`, TypeScript:
   `npm install cortexdbai`). The bare `cortexdb` package name is a different,
   unrelated package.
