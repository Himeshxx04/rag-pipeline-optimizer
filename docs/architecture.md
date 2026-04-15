# Architecture — RAG Pipeline Optimizer

## Overview

The system is designed around a core insight: no single generation strategy works best for all queries. Instead of committing to one approach, the optimizer runs multiple pipelines in parallel, evaluates each output independently, and selects the best response using a weighted scoring function that balances quality, cost, and latency.

---

## Component breakdown

### 1. Ingestion layer

**File:** `backend/app/core/ingestion.py`

PDF files are processed using PyPDF for text extraction. The raw text is split into overlapping fixed-size chunks to preserve cross-boundary context. Each chunk is embedded using OpenAI's embedding model and stored in a FAISS index persisted to disk.

Key parameters (configurable via `.env`):
- `chunk_size` — number of tokens per chunk (default: 512)
- `overlap` — token overlap between adjacent chunks (default: 64)
- `FAISS_INDEX_PATH` — local path to persist the index between sessions

---

### 2. Retrieval layer

**File:** `backend/app/core/retrieval.py`

On each query, the question is embedded using the same model as ingestion (ensuring the vector space is consistent). A nearest-neighbour search retrieves the top-k most semantically relevant chunks.

A similarity threshold filter (`SIMILARITY_THRESHOLD`, default 0.75) removes low-relevance chunks before they reach the generation layer. This prevents the LLM from being distracted by weakly related context — a common cause of hallucination in naive RAG systems.

---

### 3. Multi-pipeline generation layer

**File:** `backend/app/core/pipelines.py`

Three generation strategies run in parallel on every query:

| Pipeline | Behaviour |
|---|---|
| `strict` | Concise, factual answers. No elaboration beyond retrieved context. |
| `citations_strict` | Answers with inline source references to retrieved chunks. |
| `explanatory` | Detailed, educational tone. Best for complex or ambiguous queries. |

Running all three in parallel adds latency overhead but enables the optimizer to select the best answer for each specific query rather than committing to a single strategy upfront.

---

### 4. Judge model evaluation

**File:** `backend/app/core/judge.py`

A separate LLM instance (configurable via `JUDGE_MODEL`, default `gpt-4o`) evaluates each pipeline's response independently. The judge scores on three dimensions:

- **Quality** (0–1) — clarity, completeness, relevance to the query
- **Groundedness** (0–1) — how well the answer is supported by the retrieved chunks
- **Structure** (0–1) — coherence, formatting, readability

Responses scoring below `MIN_GROUNDEDNESS_SCORE` (default 0.6) are flagged for auto-rejection by the guardrail layer before the optimizer sees them.

Using a judge model rather than simple similarity thresholding was a deliberate design choice — similarity only tells you whether the retrieved context is relevant, not whether the generated answer actually reflects that context faithfully.

---

### 5. Balanced optimizer

**File:** `backend/app/core/optimizer.py`

The optimizer selects the best response using a weighted scoring formula:

```
score = (quality_weight × quality) − (cost_weight × cost) − (latency_weight × latency)
```

Default weights: `quality=0.6`, `cost=0.2`, `latency=0.2` (configurable via `.env`).

Cost and latency are normalised to [0,1] relative to the token budget and timeout threshold before scoring. This means the optimizer doesn't blindly pick the highest quality answer — it picks the best answer within acceptable cost and speed constraints.

---

### 6. Guardrail layer

**File:** `backend/app/core/guardrails.py`

Four guardrails run before any response is returned:

| Guardrail | What it prevents |
|---|---|
| Similarity threshold filter | Low-relevance chunks polluting generation context |
| Groundedness threshold | Answers that don't reflect the source material |
| Token budget enforcement | Single queries blowing up API cost |
| Structured error middleware | Unhandled exceptions leaking to the client |

---

### 7. Observability layer

**File:** `backend/app/core/metrics.py`

Every query logs the following to a SQLAlchemy-managed database:

- Prompt tokens, completion tokens, total tokens
- Latency per pipeline (ms)
- Cost estimate per pipeline (USD)
- Judge scores per pipeline (quality, groundedness, structure)
- Selected pipeline and final optimizer score
- Whether any guardrail triggered

This makes it possible to analyse which pipelines perform best on different query types over time.

---

## Design decisions

**Why FAISS over ChromaDB or Qdrant?**
FAISS runs entirely in-process with no external service dependency, making local development and testing faster. For a system focused on demonstrating the optimizer logic rather than production-scale vector search, this tradeoff made sense. Swapping to Qdrant for horizontal scaling is listed in the roadmap.

**Why a judge model instead of similarity-based filtering alone?**
Similarity scores measure relevance of retrieved context — they say nothing about whether the generated answer faithfully reflects that context. A document can be highly relevant but the LLM can still hallucinate details. The judge model evaluates the generated output directly, catching hallucinations that similarity thresholds miss entirely.

**Why weighted scoring over just picking the highest quality response?**
In production LLM systems, cost is a real constraint. A response scoring 0.95 on quality but using 3× the tokens of a 0.88-quality response is not always the right choice. The weighted optimizer makes this tradeoff explicit and configurable rather than ignoring it.

**Why run all three pipelines in parallel rather than routing?**
Routing (deciding upfront which pipeline to use) requires a classifier that itself can be wrong. Running all three and evaluating outputs is more reliable — the cost of running extra pipelines is bounded by the token budget guardrail.

---

## Data flow summary

```
PDF upload
    │
    ▼
Text extraction (PyPDF)
    │
    ▼
Chunking + embedding
    │
    ▼
FAISS index
    │
Query received
    │
    ▼
Query embedding + top-k retrieval
    │
Similarity threshold filter
    │
    ▼
3 pipelines run in parallel
    │
    ▼
Judge model scores each response
    │
Groundedness guardrail
    │
    ▼
Optimizer selects best response
    │
Token budget + error guardrails
    │
    ▼
Response returned + metrics logged
```
