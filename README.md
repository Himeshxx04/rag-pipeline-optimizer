# 🚀 RAG Pipeline Optimizer

A production-ready Retrieval-Augmented Generation (RAG) system with multi-pipeline generation, LLM-based evaluation, and cost-aware optimization.

## 🔥 Overview

This project implements a full RAG architecture with:

- PDF ingestion & text extraction
- Adaptive chunking
- Embedding generation
- FAISS vector indexing
- Multi-pipeline answer generation
- LLM-based answer evaluation (Judge model)
- Cost + latency aware pipeline selection
- Hallucination auto-rejection guardrail
- Query logging & metrics tracking

The system automatically selects the best answer based on quality, grounding, cost, and latency.

---

## 🧠 Architecture

Upload PDF  
→ Extract text  
→ Chunk  
→ Embed  
→ Build FAISS index  
→ Retrieve top-k chunks  
→ Run multiple generation pipelines  
→ LLM Judge evaluates answers  
→ Optimizer selects best pipeline  
→ Logs metrics & cost  

---

## ⚙️ Features

### Multi-Pipeline Generation
- strict
- citations_strict
- explanatory

### LLM Judge
Scores each answer on:
- Quality
- Groundedness
- Structure

### Balanced Optimizer
Selects answer based on:
Balanced Score =
0.6 * Quality

0.2 * Cost

0.2 * Latency


### Guardrails
- Token budget enforcement
- Similarity threshold filtering
- Auto-reject low grounded responses
- Structured error handling middleware

---

## 📊 Metrics Captured

- Prompt tokens
- Completion tokens
- Total tokens
- Latency
- Cost estimation
- Judge evaluation scores

---

## 🏗️ Tech Stack

Backend:
- FastAPI
- SQLAlchemy
- FAISS
- OpenAI API

Frontend:
- React (Vite scaffold)

---

## 🚀 Future Work

- Docker deployment
- Cloud storage abstraction
- Multi-worker shared storage
- Horizontal scaling
- CI/CD integration