# Costs — what CortexDB costs to run

Three cost lines, in the order they surprise people:

1. **Hosting** — the VM / instance running CortexDB (self-hosted) or the managed-instance fee (cloud).
2. **Ingest** — embedding + enrichment, driven by **how much you write** (one-time per event).
3. **Answers** — the answer lane, driven by **how much you ask**. The official docs'
   rule of thumb: *"Question volume drives the cost, not corpus size."*

All figures USD, list prices, September 2026. Items marked **[modeled]** are estimates
from the assumptions stated — verify against your own workload with
`GET /v1/admin/usage` (Admin Console → Tokens & cost), which reports exact tokens
per role/model. Official cost page: <https://cortexdb.ai/docs/operations/cost-planning>.

---

## 1. Hosting — instance size by data size

Official rule of thumb for text-heavy workloads at the default embeddings
(`text-embedding-3-small`, 1536 dims, TQ2 quantization) — from
[storage & clustering](https://cortexdb.ai/docs/operations/storage-cluster):

| Events stored | Disk footprint | Memory (cache + HNSW) | Instance class (AWS anchor) | Indicative $/mo (on-demand) |
|---|---|---|---|---|
| **100 K** (pilot) | ~2 GB | ~1 GB | `t3.medium` (2 vCPU / 4 GB) | **~$30** |
| **1 M** (small team) | ~15 GB | ~6 GB | `r6i.large` (2 vCPU / 16 GB) | **~$185** |
| **10 M** (department) | ~120 GB | ~40 GB | `r6i.2xlarge` (8 vCPU / 64 GB) | **~$740** |
| **100 M+** (enterprise) | ~1.1 TB | ~350 GB | very large single box (e.g. `r6i.12xlarge`, 384 GB) | **~$2,200+ — talk to us** |

- Disk footprint includes everything derived from the append-only WAL: RocksDB,
  HNSW vectors, Tantivy fulltext, knowledge graph, materialized views — budget
  block storage at ~$0.08/GB-mo on top of the instance (≈ $1 at 1 M events,
  ≈ $10 at 10 M, ≈ $90 at 100 M).
- **Single-node is the only supported topology today**, production-ready up to
  ~10 M events. Cluster flags are refused at startup (`CLUSTER_MODE_UNSUPPORTED`)
  and clustering is experimental / not operational — above ~10 M events the
  official guidance is to plan a very large single box, not a cluster. Talk to
  us before committing to a 100 M+ design.
- Anchors are AWS on-demand list prices (`r6i` ≈ $0.252/hr per 16 GB of RAM;
  GCP `n2-highmem` and Azure `E`-series price within ±20% of the same class;
  reserved/committed-use cuts these 40–60%). [modeled] — check current pricing.
- **Managed instance** (`https://<tenant>.cortexdb.ai`, Mode B in
  [`../00-cloud/CLOUD.md`](../00-cloud/CLOUD.md)): hosting is included in the
  managed fee — you don't size anything.
- Local Ollama embeddings add an Ollama container + model (~1–6 GB disk — see
  [`../01-self-host/`](../01-self-host/)) and CPU (~30 ms/embedding).
- The **RPO is your backup cadence** — the supported backup is a verified cold
  backup of the data directory (server stopped), so schedule maintenance windows
  ([backups & DR](https://cortexdb.ai/docs/enterprise/backups-dr)).

## 2. Ingest — embedding + enrichment (per event, one-time)

From the official cost-planning page:

| Item | Cost |
|---|---|
| Load **and enrich 10,000 events** (one time) | **≈ $4** |
| Each additional 1,000 events | **≈ $0.40** |
| Embedding (`text-embedding-3-small`) | $0.02 per **million** tokens — negligible at any size |
| Local embeddings (Ollama) | $0 (trades ~3–5 accuracy points; ~30 ms/embedding on CPU) |

Examples: **100 K events ≈ $40 one-time · 1 M events ≈ $400 · 10 M events ≈ $4,000**.
Enrichment (fact/belief extraction, `gpt-4o-mini` at $0.15/$0.60 per M tokens) is
the bulk of that; re-embedding a whole corpus on a dimension change costs roughly
the embedding line only (~$30 at 10 M events [modeled: 10 M × ~150 tokens × $0.02/M]).
Assumption from the docs: events average **~150 tokens** — longer documents cost
more to enrich. Enrichment **off** = ingest cost drops to ~$0 (raw events + search
only; Facts/Beliefs/Understanding stay empty).

## 3. Answers — the ongoing line

| Item | Cost |
|---|---|
| Each answered question — `gpt-5.6-terra` (recommended) | **$0.02–0.04** |
| Each answered question — `gpt-5.6-luna` (budget) | $0.002–0.004 |
| Each answered question — `gpt-5.6-sol` (premium) | $0.04–0.07 |
| Each **search without** a generated answer (`/v1/recall`) | **< $0.001** |

Monthly at Terra: **1 K answers ≈ $22–40 · 10 K ≈ $220–400 · 100 K ≈ $2,200–4,000**
(using ~10 K input tokens per question, reasoning tokens billed as output). At Luna,
10 K answers/mo ≈ **$22–40**.

Practical levers:

- Most read traffic should be **recall + your own model** (sub-cent per query) —
  reserve the answer lane for user-facing Q&A.
- Recalls are cheap; **question volume, not corpus size, is the line to watch.**
- Set `CORTEX_MODEL_PRICES` if you use models missing from the built-in price book,
  or the ledger understates cost (see
  [cost planning](https://cortexdb.ai/docs/operations/cost-planning) for the override string).
- A verifier lane (active if `CORTEX_VERIFIER_API_KEY` **or `OPENAI_API_KEY`** is set)
  adds one `gpt-4.1` call per verified answer.

## Worked examples (self-hosted)

| Profile | One-time ingest | Ongoing $/mo |
|---|---|---|
| **Pilot** — 100 K events, 1 K answers/mo (Terra) | ~$40 | ~$30 hosting + ~$30 answers ≈ **$60** |
| **Team** — 1 M events, 10 K answers/mo (Terra) | ~$400 | ~$185 hosting + ~$300 answers ≈ **$485** |
| **Department** — 10 M events, 10 K answers/mo (Terra), Luna for bulk flows | ~$4,000 | ~$740 hosting + ~$300–400 answers ≈ **$1,100** |

[modeled from the table above; cloud-managed hosting replaces the hosting line with
your managed-instance fee]

---

## Measure, don't trust this page

`GET /v1/admin/usage` gives exact per-role/per-model token counts; the Admin
Console renders it as **Tokens & cost**. Re-check the official page before quoting
numbers externally: <https://cortexdb.ai/docs/operations/cost-planning>.
