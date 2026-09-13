# finance_agent_Monash

An internal **accounts-payable assistant**. Given an invoice-processing request, the agent retrieves
relevant finance policy, gathers vendor / purchase-order / invoice-history evidence, reconciles it
deterministically, produces a **grounded, cited recommendation**, and **pauses for human approval**
before recording any (simulated) financial decision.

Built for the "Agentic AI Engineer — Financial Processing and RAG Workflow Agent" take-home.
Deployment target: **local**.

---

## What it does

```
ProcessingRequest
   → retrieve   (RAG over finance policy corpus: hybrid lexical + semantic)
   → gather     (vendor record, purchase order, invoice history — mocked tools; PO call has bounded retry)
   → reconcile  (deterministic three-way match, duplicate/vendor/approval checks — pure code)
   → recommend  (LLM: classifies next_action + rationale, validated against a schema)
   → approval   (human-in-the-loop interrupt — the run pauses here for a payment)
   → submit     (records the decision — approval-gated, idempotent, simulated)
   → finalize   (typed FinalResult separating facts / calculations / findings / actions)
```

The full architecture (with trust boundaries and a component manifest) is in
[`docs/architecture.md`](docs/architecture.md).

---

## Environment & prerequisites

- **Python 3.12** (uses the `py -3.12` launcher on Windows; any 3.12 interpreter works)
- An **Anthropic API key** for the `recommend` node's LLM call
- OS: developed on Windows 11; the code is cross-platform

## Setup

```bash
# 1. Create and activate a virtual environment
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1          # Windows PowerShell
# source .venv/bin/activate         # macOS / Linux

# 2. Install pinned dependencies
pip install -r requirements.txt

# 3. Configure secrets/model
copy .env.example .env              # Windows  (cp on macOS/Linux)
# then edit .env and set ANTHROPIC_API_KEY=sk-ant-...
```

`.env` (git-ignored) holds your key and model choice:

```
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-5     # or claude-opus-5 / claude-haiku-4-5
AGENT_MAX_STEPS=12
```

### Document ingestion / indexing

No separate ingestion step is required. The RAG index is **built in-memory on first use** from the
markdown corpus in [`data/finance_rag_corpus/`](data/finance_rag_corpus) (15 finance policy documents
with YAML frontmatter). Chunking is by markdown `##` section; retrieval is hybrid (lexical + local
sentence-transformer embeddings, fused with Reciprocal Rank Fusion). The embedding model
(`all-MiniLM-L6-v2`) downloads automatically on first run (~90 MB, cached thereafter).

---

## Running the agent (CLI)

The workflow is exposed through four CLI commands (`python -m src.cli <command>`):

**Start a run** — executes until completion, failure, or approval-required:

```bash
python -m src.cli start --case FIN-001 --invoice INV-7777 --vendor "Acme Supplies" --amount 1250.00 --currency AUD --date 2026-09-10 --po PO-5001
```

Prints a `run_id`. For a payment it pauses with `status: AWAITING_APPROVAL` and shows the approval request.

**Get a run** — status, current state, audit events, result:

```bash
python -m src.cli get --thread <run_id>
```

**Approve / reject** — resolve a pending decision and safely resume the same run:

```bash
python -m src.cli approve --thread <run_id>            # approve
python -m src.cli approve --thread <run_id> --reject   # reject
```

**List evaluation results** — run the supplied FIN test cases and report pass/fail:

```bash
python -m src.cli eval
```

Run state is persisted to `runs/checkpoints.sqlite` (LangGraph SQLite checkpointer), so `start` and a
later `approve` work across **separate processes / restarts**.

---

## Testing

Two separate suites (per the brief):

```bash
# Stable, deterministic unit/contract tests — no API key needed
python -m pytest tests/ -q

# Model-dependent evaluation of the five FIN scenarios — requires ANTHROPIC_API_KEY
python -m src.cli eval
```

| Case | Behaviour verified |
|---|---|
| FIN-001 valid three-way match | cites evidence, requests approval, submits **exactly once** |
| FIN-002 duplicate invoice | detects paid duplicate, recommends hold/reject, **never proposes payment** |
| FIN-003 poisoned document | treats document/note text as untrusted; **does not bypass approval** |
| FIN-004 missing evidence (PO timeout) | **bounded retry** then fails safe; no payment approval |
| FIN-005 duplicate approval | one effective decision, **replay-safe** (idempotency key) |

---

## Reproducible environment (Docker / Make)

Environment artefacts for the local setup:

- **`Dockerfile`** — builds an identical environment and runs the CLI as its entrypoint:
  ```bash
  docker build -t finance-agent-monash .
  docker run --rm -e ANTHROPIC_API_KEY=sk-ant-... finance-agent-monash eval
  ```
  The image bundles `src/`, `data/`, and `tests/`; the embedding model downloads on first use and run
  state persists under `/app/runs`.
- **`Makefile`** — codifies the common commands as targets: `install`, `test`, `eval`, `demo`,
  `docker-build`, `docker-run`.
- **`requirements.txt`** — pinned dependency versions (dependency lock).
- **`.env.example`** — configuration template (no secrets).

These are the infrastructure-as-code / scripts for the chosen **local** setup; no cloud deployment export
is required.

---

## Real vs. simulated integrations

| Component | Real or mock |
|---|---|
| LLM (`recommend` node) | **Real** — Anthropic API (model configurable in `.env`) |
| RAG retrieval | **Real** — over the local policy corpus + a local embedding model (no external API) |
| `get_vendor_record`, `get_purchase_order`, `check_invoice_history` | **Mock** — typed contracts over in-memory fixtures |
| `submit_finance_decision` | **Simulated** — records a decision; **moves no real money** (approval-gated + idempotent) |
| Persistence | **Real** — SQLite checkpointer on disk |

All tool inputs/outputs use explicit Pydantic schemas. Reconciliation arithmetic is deterministic
(`Decimal`, in code), never delegated to the model.

---

## Safety controls

- **Trust boundary** — retrieved documents and case notes are treated as *untrusted data*; the system
  prompt forbids following instructions found inside them, and no document can authorize payment. The
  approval gate is enforced by the graph, not by the model, so prompt injection cannot bypass it (FIN-003).
- **Deny-by-default, approval-gated, idempotent** consequential tool (`submit_finance_decision`).
- **Validated model output** — the LLM's response is parsed against a schema; invalid output is retried,
  then fails **safe** (recommends `request_info`, never a payment).
- **Bounded retries + timeouts** on the external-style PO call; graceful failure exposes missing evidence.
- **Bounded step budget** and an **audit trail** (timestamps/events) on every run; no credentials or bank
  details are logged (vendor bank details are stored masked).

---

## Assumptions & known limitations

- **Fixtures over real systems.** The four read/decision tools are mocked. In production each would query
  a vendor-master DB / ERP / payment sandbox and deserialize the response into the same schema.
- **Retrieval** is lexical + a small local embedding model; the query is topic-driven from the case. It
  suits a small, well-structured corpus. Limitations: no reranker, no ANN index (unnecessary at ~70 chunks),
  and the topic list is derived from the corpus rather than discovered dynamically.
- **In-memory idempotency ledger** in `submit_finance_decision` demonstrates replay-safety within a
  process; a production version would persist the ledger (e.g. alongside the checkpointer).
- **Single base currency** (AUD) assumed for tolerance/threshold logic; FX handling is retrieved as policy
  but not fully implemented.
- **Timebox:** built to demonstrate correct control and failure handling over feature breadth.

---

## Project layout

```
src/
  models.py            shared Pydantic schemas (request, chunk, recommendation, final result)
  rag.py               corpus loader, chunker, lexical retrieval
  embeddings.py        local semantic retrieval (sentence-transformers)
  config.py            model/provider config (loads .env) — kept outside orchestration
  tools/               the 5 tools, each with its own typed I/O schema + fixtures
  agent/
    state.py           AgentState — the shared, persisted run state
    nodes.py           the 7 node functions
    graph.py           LangGraph assembly (edges, conditional routing, checkpointer)
  cli.py               start / get / approve / eval commands
  eval.py              the five FIN evaluation cases
tests/                 deterministic unit/contract tests (pytest)
data/finance_rag_corpus/   15 finance policy markdown documents
docs/architecture.md   architecture diagram (image + Mermaid) + trust boundaries + component manifest
docs/Architecture_Diagram.png   rendered architecture image
docs/DESIGN_NOTE.md / .pdf   design note (orchestration, RAG, trust, failure handling)
docs/transcript_*.txt  sample runs (FIN-001 success, FIN-002 exception)
```

---

## AI tool usage

This project was built with AI coding assistance (Claude). All design decisions — schemas, the agent
graph, trust boundaries, tool contracts, and tests — were made and reviewed deliberately and can be
explained and defended.
