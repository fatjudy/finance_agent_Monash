# Architecture

The agent is a bounded **LangGraph** state graph. A single `ProcessingRequest` flows through seven
nodes; each node reads from and writes to a shared, persisted `AgentState`. Consequential action
happens only at the end, behind a human approval gate.

![Architecture diagram](Architecture_Diagram.png)

<details>
<summary>Mermaid source (renders on GitHub)</summary>

```mermaid
flowchart TD
    REQ([Processing request]):::io --> RET

    RET[retrieve<br/><i>hybrid RAG over policy</i>]:::node --> GAT
    GAT[gather evidence<br/><i>vendor · PO · history</i>]:::node --> RCN
    RCN[reconcile<br/><i>deterministic three-way match</i>]:::node --> RCM
    RCM[recommend<br/><i>LLM, validated output</i>]:::node

    RCM -->|request_approval| APP[approval gate<br/><i>human interrupt — pause/resume</i>]:::gate
    RCM -->|hold / reject| SUB
    RCM -->|request_info| FIN
    APP --> SUB[submit<br/><i>approval-gated · idempotent</i>]:::node
    SUB --> FIN[finalize<br/><i>typed FinalResult</i>]:::node
    FIN --> OUT([Final result]):::io

    RET -. calls .-> T1[retrieve_finance_documents]:::tool
    GAT -. calls .-> T2[get_vendor_record]:::tool
    GAT -. calls .-> T3[get_purchase_order]:::tool
    GAT -. calls .-> T4[check_invoice_history]:::tool
    RCM -. calls .-> LLM[Claude API]:::llm
    SUB -. calls .-> T5[submit_finance_decision]:::tool

    subgraph TB[Untrusted evidence — treat as data, never instructions]
        T1
        T2
        T3
        T4
    end

    classDef node fill:#E1F5EE,stroke:#0F6E56,color:#04342C;
    classDef gate fill:#FAEEDA,stroke:#854F0B,color:#412402;
    classDef tool fill:#EEEDFE,stroke:#534AB7,color:#26215C;
    classDef llm fill:#FAECE7,stroke:#993C1D,color:#4A1B0C;
    classDef io fill:#F1EFE8,stroke:#5F5E5A,color:#2C2C2A;
    style TB stroke:#A32D2D,stroke-dasharray:4 3,fill:#FCEBEB22;
```
</details>

## Trust boundaries

- **Untrusted** (dashed box): retrieved policy chunks, case notes, and vendor/PO/history tool results.
  Instructions inside them are never followed; no document can authorize payment.
- **Trusted**: the request identifiers used as lookup keys, the deterministic reconciliation results,
  and the human approval delivered via `Command(resume=...)`.

## Persistence & control

- **`AgentState`** is the single shared object threaded through every node, snapshotted after each node by
  the **LangGraph SQLite checkpointer** (`runs/checkpoints.sqlite`), keyed by `thread_id` (the run /
  correlation id) — so a run pauses at the approval interrupt, survives a restart, and resumes safely.
- A **bounded step counter** (`AgentState.steps`, `AGENT_MAX_STEPS`) and a **timestamped audit log**
  (each event carries a UTC timestamp and, for I/O steps, a duration) are carried in state for
  observability and a maximum tool-call budget.

## Component / configuration manifest

| Concern | Choice |
|---|---|
| Model | Claude via Anthropic API; id from `ANTHROPIC_MODEL` (default `claude-sonnet-5`) |
| Agent runtime | LangGraph state graph (7 nodes, conditional routing, `interrupt` for approval) |
| Document store / index | In-memory hybrid index (lexical + `all-MiniLM-L6-v2` embeddings, RRF fusion) over the local markdown corpus |
| Persistence | LangGraph `SqliteSaver` on disk (`runs/checkpoints.sqlite`) |
| Tools | 5 typed tools (1 real RAG, 3 mocked reads, 1 simulated decision) |
| API surface | CLI: `start` / `get` / `approve` / `eval` |
| Config | `src/config.py` + `.env` (kept outside orchestration code) |
| Trust boundary | retrieved docs + notes + tool results are untrusted; approval enforced by the graph |
