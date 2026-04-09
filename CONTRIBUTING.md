# Contributing to RAG Pipeline Optimizer

Thanks for your interest in contributing. This document covers how to get set up, what's worth working on, and how to submit changes cleanly.

---

## Getting started

```bash
# 1. Fork and clone
git clone https://github.com/YOUR_USERNAME/rag-pipeline-optimizer.git
cd rag-pipeline-optimizer

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# 5. Run the backend
uvicorn backend.app.main:app --reload
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

---

## Areas open for contribution

| Area | What's needed |
|---|---|
| **New generation pipelines** | Add a `concise` or `structured_json` pipeline alongside the existing strict/citation/explanatory ones |
| **Alternative vector stores** | Swap FAISS for ChromaDB or Qdrant with a common interface |
| **Chunking strategies** | Add sentence-level or semantic chunking as alternatives to fixed-size |
| **Judge model improvements** | Better prompts or a smaller fine-tuned judge to reduce cost |
| **Docker support** | `Dockerfile` + `docker-compose.yml` for one-command setup |
| **Tests** | Unit tests for the optimizer scoring logic and guardrails |
| **Streaming responses** | SSE-based streaming from FastAPI for real-time token output |

---

## Coding conventions

- Python 3.10+
- Follow existing file structure — routers in `backend/app/routers/`, core logic in `backend/app/core/`
- Use type hints on all function signatures
- Docstrings on all public functions (Google style)
- Keep each function under 40 lines — split if it gets longer

---

## Submitting a pull request

1. Create a branch: `git checkout -b feat/your-feature-name`
2. Make your changes with clear, atomic commits
3. Test manually against the `/docs` UI
4. Open a PR with a short description of what you changed and why

For bugs, open an issue first describing the behaviour and reproduction steps.

---

## Questions

Open an issue or reach out via [LinkedIn](https://www.linkedin.com/in/himesh-pandey-66968a213/).
