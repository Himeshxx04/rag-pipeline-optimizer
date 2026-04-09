# RAG Pipeline Optimizer

A production-grade Retrieval-Augmented Generation system with multi-pipeline generation, automated LLM-based evaluation, and cost-aware response selection.

Built with FastAPI, FAISS, and OpenAI — designed to go beyond basic RAG demos by solving the real problems: answer quality variance, hallucination, and unpredictable inference cost.

---

## What makes this different from a typical RAG setup

Most RAG implementations pick one generation strategy and hope for the best. This system runs **multiple pipelines in parallel**, has an **LLM judge evaluate each response**, and uses a **weighted optimizer to select the best answer** based on quality, cost, and latency — automatically.

```
Upload PDF
   │
   ▼
Extract text → Chunk → Embed → FAISS index
                                    │
                          Query comes in
                                    │
                          Retrieve top-k chunks
                                    │
               ┌────────────────────┼────────────────────┐
               ▼                    ▼                    ▼
         strict pipeline    citation pipeline    explanatory pipeline
               │                    │                    │
               └────────────────────┼────────────────────┘
                                    │
                             LLM Judge scores each
                          (quality · groundedness · structure)
                                    │
                          Optimizer selects best
                     (0.6×quality − 0.2×cost − 0.2×latency)
                                    │
                          Guardrails check response
                     (hallucination rejection · token budget)
                                    │
                              Final answer
```

---

## Features

### Multi-pipeline generation
Three answer strategies run on every query:
- **Strict** — concise, factual, no elaboration beyond the context
- **Citation-based** — answers with inline source references
- **Explanatory** — detailed, educational tone for complex queries

### LLM Judge evaluation
A separate judge model scores each pipeline's response on:
- **Quality** — clarity, completeness, relevance to the query
- **Groundedness** — how well the answer is supported by retrieved context
- **Structure** — coherence and formatting

### Balanced optimizer
Selects the best response using a weighted scoring formula:

```
score = (0.6 × quality) − (0.2 × cost) − (0.2 × latency)
```

Weights are configurable via `.env`.

### Guardrails
- **Hallucination auto-rejection** — responses below the groundedness threshold are discarded
- **Similarity threshold filtering** — low-relevance chunks are excluded before generation
- **Token budget enforcement** — hard cap on tokens per generation request
- **Structured error handling middleware** — all pipeline failures are caught and logged

### Full observability
Every query logs: prompt tokens, completion tokens, total tokens, latency, cost estimate, and judge scores — stored in SQLAlchemy for analysis.

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI + Uvicorn |
| Vector search | FAISS |
| LLM + embeddings | OpenAI API |
| ORM / metrics store | SQLAlchemy |
| Frontend | React (Vite) |
| Observability | LangSmith |

---

## Getting started

### Prerequisites
- Python 3.10+
- Node.js 18+ (for frontend)
- An OpenAI API key

### Setup

```bash
# 1. Clone the repo
git clone https://github.com/Himeshxx04/rag-pipeline-optimizer.git
cd rag-pipeline-optimizer

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Open .env and add your OPENAI_API_KEY
```

### Run the backend

```bash
uvicorn backend.app.main:app --reload
```

API available at `http://localhost:8000`  
Interactive docs at `http://localhost:8000/docs`

### Run the frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend available at `http://localhost:5173`

---

## Usage

1. Open the frontend and upload a PDF
2. The system ingests, chunks, embeds, and indexes it automatically
3. Ask a question — all three pipelines run, the judge evaluates, the optimizer picks the best answer
4. Metrics (tokens, cost, latency, scores) are logged per query and viewable in the dashboard

---

## Configuration

All settings are controlled via `.env`. Key options:

| Variable | Default | Description |
|---|---|---|
| `OPENAI_MODEL` | `gpt-4o-mini` | Model for generation pipelines |
| `JUDGE_MODEL` | `gpt-4o` | Model for answer evaluation |
| `QUALITY_WEIGHT` | `0.6` | Weight for quality in optimizer score |
| `SIMILARITY_THRESHOLD` | `0.75` | Min cosine similarity for chunk retrieval |
| `TOKEN_BUDGET` | `2000` | Max tokens per generation request |
| `MIN_GROUNDEDNESS_SCORE` | `0.6` | Auto-reject threshold for hallucination guard |
| `TOP_K_CHUNKS` | `5` | Number of chunks retrieved per query |

See `.env.example` for the full list.

---

## Roadmap

- [ ] Docker + docker-compose for one-command setup
- [ ] Cloud storage abstraction (S3 / GCS) for PDF uploads
- [ ] Multi-worker shared FAISS index
- [ ] Streaming responses via SSE
- [ ] CI/CD pipeline
- [ ] Horizontal scaling support

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup instructions and open contribution areas.

---

## Author

**Himesh Pandey** — Final year ECE @ PES University, Bangalore (2026)  
[LinkedIn](https://www.linkedin.com/in/himesh-pandey-66968a213/) · [GitHub](https://github.com/Himeshxx04) · pandeyhimesh09@gmail.com
