from __future__ import annotations

import os
import uuid
import time
import shutil
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple, Optional

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.api.response import ok

from app.db.deps import get_db
from app.db.models import Document, QueryLog

from app.services.text_extractor import extract_text_from_pdf
from app.services.text_storage import save_extracted_text

from app.services.chunker import chunk_text
from app.services.chunk_storage import save_chunks, load_chunks

from app.services.embedding import embed_texts
from app.services.embedding_storage import save_embeddings

from app.services.faiss_store import build_faiss_index, save_index, load_index, search_index
from app.services.generator import generate_answer
from app.services.judge import judge_pipelines

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
logger = logging.getLogger("rag.documents")

# -----------------------------------------------------------------------------
# Router & config
# -----------------------------------------------------------------------------
router = APIRouter(prefix="/documents", tags=["documents"])

UPLOAD_DIR = os.getenv("STORAGE_PATH", "data/uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

DEFAULT_CHUNK_SIZE = 1000
DEFAULT_OVERLAP = 200
DEFAULT_TOP_K = 5

MAX_PROMPT_TOKENS = 3000
SAFETY_BUFFER_TOKENS = 300

# Pricing (simple estimate; ok for optimizer comparisons)
INPUT_PRICE_PER_1K = 0.005
OUTPUT_PRICE_PER_1K = 0.015

# Optimizer config
PIPELINES = ["strict", "citations_strict", "explanatory"]

# Hallucination auto-rejection threshold
MIN_GROUNDED_SCORE = 6.0

# BALANCED mode weights (sum to 1.0)
# Higher judge score is better; lower cost/latency is better.
W_QUALITY = 0.60   # uses judge_overall_score (0..10)
W_COST = 0.20      # normalized 0..1 (higher = more expensive)
W_LATENCY = 0.20   # normalized 0..1 (higher = slower)

# Simple cache knobs (per-process RAM cache)
CACHE_TTL_SECONDS = 30 * 60  # 30 minutes
CACHE_MAX_DOCS = 32          # keep recent docs in RAM

# -----------------------------------------------------------------------------
# In-memory caches (per-process)
# NOTE: if uvicorn runs multiple workers, each worker has its own cache.
# -----------------------------------------------------------------------------
@dataclass
class CacheEntry:
    value: Any
    ts: float


_chunks_cache: Dict[str, CacheEntry] = {}  # doc_id -> List[str]
_index_cache: Dict[str, CacheEntry] = {}   # doc_id -> faiss index


def _now() -> float:
    return time.time()


def _cache_get(cache: Dict[str, CacheEntry], key: str) -> Optional[Any]:
    entry = cache.get(key)
    if not entry:
        return None
    if (_now() - entry.ts) > CACHE_TTL_SECONDS:
        cache.pop(key, None)
        return None
    return entry.value


def _cache_set(cache: Dict[str, CacheEntry], key: str, value: Any) -> None:
    if key not in cache and len(cache) >= CACHE_MAX_DOCS:
        oldest_key = min(cache.items(), key=lambda kv: kv[1].ts)[0]
        cache.pop(oldest_key, None)
    cache[key] = CacheEntry(value=value, ts=_now())


def _cache_invalidate(doc_id: str) -> None:
    _chunks_cache.pop(doc_id, None)
    _index_cache.pop(doc_id, None)


def _doc_folder(doc_id: str) -> str:
    return os.path.join(UPLOAD_DIR, doc_id)


def _safe_pdf_filename(name: str) -> str:
    """
    Prevent Windows/DB encoding issues with emoji / non-ascii filenames.
    Keep it simple: strip directories and replace non-ascii with '_'.
    """
    base = os.path.basename(name or "")
    if not base:
        base = "upload.pdf"
    safe = "".join(ch if ord(ch) < 128 else "_" for ch in base)
    return safe if safe else "upload.pdf"


def _ensure_doc_exists(db: Session, doc_id: str) -> Document:
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found in database")
    return doc


def _ensure_folder_exists(doc_id: str) -> str:
    folder = _doc_folder(doc_id)
    if not os.path.isdir(folder):
        raise HTTPException(status_code=404, detail="Document folder not found on disk")
    return folder


def _get_chunks_and_index(doc_id: str) -> Tuple[List[str], Any]:
    """
    Central loader + cache.
    """
    cached_chunks = _cache_get(_chunks_cache, doc_id)
    cached_index = _cache_get(_index_cache, doc_id)

    if cached_chunks is not None and cached_index is not None:
        return cached_chunks, cached_index

    folder = _ensure_folder_exists(doc_id)

    chunks = cached_chunks if cached_chunks is not None else load_chunks(folder)
    index = cached_index if cached_index is not None else load_index(folder)

    _cache_set(_chunks_cache, doc_id, chunks)
    _cache_set(_index_cache, doc_id, index)

    return chunks, index


def estimate_tokens(text: str) -> int:
    # Rough estimate: 1 token ≈ 4 chars (good enough for guardrails)
    return max(1, len(text) // 4)


def estimate_cost_usd(prompt_tokens: int, completion_tokens: int) -> float:
    return (prompt_tokens / 1000) * INPUT_PRICE_PER_1K + (completion_tokens / 1000) * OUTPUT_PRICE_PER_1K


def _normalize(value: float, min_v: float, max_v: float) -> float:
    """
    Normalize to [0, 1]. If range is 0, return 0 (no penalty difference).
    """
    if max_v == min_v:
        return 0.0
    return (value - min_v) / (max_v - min_v)


# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------
@router.post("/upload")
def upload_document(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    chunk_size: int = Query(DEFAULT_CHUNK_SIZE, ge=200, le=4000),
    overlap: int = Query(DEFAULT_OVERLAP, ge=0, le=1000),
):
    """
    Upload PDF -> extract -> chunk -> embed -> FAISS index.
    Saves artifacts on disk under {UPLOAD_DIR}/{doc_id}/
    Stores metadata in DB.
    """
    if overlap >= chunk_size:
        raise HTTPException(status_code=400, detail="overlap must be < chunk_size")

    filename = _safe_pdf_filename(file.filename)
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF uploads are supported")

    doc_id = str(uuid.uuid4())
    folder = _doc_folder(doc_id)
    os.makedirs(folder, exist_ok=True)

    file_path = os.path.join(folder, filename)

    # Create DB row early
    doc = Document(
        id=doc_id,
        filename=filename,
        status="uploaded",
        num_chunks=0,
        num_embeddings=0,
    )
    db.add(doc)
    db.commit()

    try:
        # 1) Save PDF
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # 2) Extract text
        extracted_text = extract_text_from_pdf(file_path)
        if not extracted_text or not extracted_text.strip():
            doc.status = "failed"
            db.commit()
            raise HTTPException(status_code=400, detail="Could not extract any text from the PDF")

        save_extracted_text(folder, extracted_text)

        # 3) Chunk
        chunks: List[str] = chunk_text(extracted_text, chunk_size=chunk_size, overlap=overlap)
        if not chunks:
            doc.status = "failed"
            db.commit()
            raise HTTPException(status_code=400, detail="Chunking produced 0 chunks")

        save_chunks(folder, chunks)

        doc.status = "chunked"
        doc.num_chunks = len(chunks)
        db.commit()

        # 4) Embed
        embeddings = embed_texts(chunks)
        if embeddings is None or len(embeddings) != len(chunks):
            doc.status = "failed"
            db.commit()
            raise HTTPException(
                status_code=500,
                detail=f"Embedding mismatch: chunks={len(chunks)} embeddings={0 if embeddings is None else len(embeddings)}"
            )

        save_embeddings(folder, embeddings)

        doc.status = "embedded"
        doc.num_embeddings = len(embeddings)
        db.commit()

        # 5) FAISS
        index = build_faiss_index(embeddings)
        save_index(folder, index)

        doc.status = "indexed"
        db.commit()

        # Warm cache
        _cache_set(_chunks_cache, doc_id, chunks)
        _cache_set(_index_cache, doc_id, index)

        return ok({
            "doc_id": doc.id,
            "filename": doc.filename,
            "status": doc.status,
            "num_chunks": doc.num_chunks,
            "num_embeddings": doc.num_embeddings,
        }, request)

    except HTTPException:
        if doc.status != "failed":
            doc.status = "failed"
            db.commit()
        raise

    except Exception as e:
        logger.exception("Upload pipeline failed for doc_id=%s: %s", doc_id, str(e))
        doc.status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail="Upload pipeline failed. Check server logs.") from e

    finally:
        try:
            file.file.close()
        except Exception:
            pass


@router.get("")
def list_documents(request: Request, db: Session = Depends(get_db)):
    docs = db.query(Document).order_by(Document.created_at.desc()).all()
    return ok([
        {
            "doc_id": d.id,
            "filename": d.filename,
            "status": d.status,
            "num_chunks": d.num_chunks,
            "num_embeddings": d.num_embeddings,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in docs
    ], request)


@router.get("/{doc_id}")
def get_document(request: Request, doc_id: str, db: Session = Depends(get_db)):
    d = _ensure_doc_exists(db, doc_id)
    return ok({
        "doc_id": d.id,
        "filename": d.filename,
        "status": d.status,
        "num_chunks": d.num_chunks,
        "num_embeddings": d.num_embeddings,
        "created_at": d.created_at.isoformat() if d.created_at else None,
        "similarity_threshold": getattr(d, "similarity_threshold", None),
    }, request)


@router.get("/{doc_id}/search")
def search_document(
    request: Request,
    doc_id: str,
    query: str,
    top_k: int = Query(DEFAULT_TOP_K, ge=1, le=20),
    db: Session = Depends(get_db),
):
    """
    Retrieval-only endpoint (no GPT).
    """
    doc = _ensure_doc_exists(db, doc_id)
    if doc.status != "indexed":
        raise HTTPException(status_code=400, detail=f"Document not ready. status={doc.status}")

    chunks, index = _get_chunks_and_index(doc_id)

    q_embedding = embed_texts([query])[0]
    indices, scores = search_index(index, q_embedding, top_k)

    results = []
    for idx, score in zip(indices, scores):
        if idx == -1:
            continue
        i = int(idx)
        results.append({"chunk_index": i, "score": float(score), "text": chunks[i]})

    return ok({"doc_id": doc_id, "query": query, "results": results}, request)


@router.post("/{doc_id}/ask")
def ask_document(
    request: Request,
    doc_id: str,
    question: str,
    top_k: int = Query(DEFAULT_TOP_K, ge=1, le=20),
    db: Session = Depends(get_db),
):
    """
    Full RAG + Optimizer (BALANCED mode):
    embed question -> retrieve chunks (threshold + token guardrail)
    -> run multiple generation pipelines
    -> judge pipelines
    -> auto-reject low-grounded (hallucination guardrail)
    -> BALANCED selection: quality - cost - latency (normalized)
    -> persist QueryLog
    """
    doc = _ensure_doc_exists(db, doc_id)
    if doc.status != "indexed":
        raise HTTPException(status_code=400, detail=f"Document not ready. status={doc.status}")

    chunks, index = _get_chunks_and_index(doc_id)

    # 1) Embed question
    q_embedding = embed_texts([question])[0]

    # 2) Retrieve raw results
    indices, scores = search_index(index, q_embedding, top_k)

    retrieved_chunks: List[str] = []
    sources: List[Dict[str, Any]] = []

    threshold = getattr(doc, "similarity_threshold", 0.0)

    # -------- TOKEN BUDGET GUARDRAIL --------
    token_budget = MAX_PROMPT_TOKENS - SAFETY_BUFFER_TOKENS
    used_tokens = estimate_tokens(question)

    for idx, score in zip(indices, scores):
        if idx == -1:
            continue

        score = float(score)
        if score < threshold:
            continue

        i = int(idx)
        chunk_text = chunks[i]
        chunk_tokens = estimate_tokens(chunk_text)

        if used_tokens + chunk_tokens > token_budget:
            break

        retrieved_chunks.append(chunk_text)
        sources.append({"chunk_index": i, "score": score})
        used_tokens += chunk_tokens

    if not retrieved_chunks:
        return ok({
            "doc_id": doc_id,
            "question": question,
            "answer": "No sufficiently relevant context found within token budget.",
            "sources": [],
            "metrics": {
                "model_name": None,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "generation_time_ms": 0.0,
                "cost_usd": 0.0,
                "pipeline_selected": None,
            },
        }, request)

    # 3) Run all pipelines
    pipeline_results: List[Dict[str, Any]] = []
    for pipeline_name in PIPELINES:
        result = generate_answer(
            question=question,
            context_chunks=retrieved_chunks,
            pipeline=pipeline_name,
        )

        # attach cost estimate (used for selection)
        p_tokens = int(result.get("prompt_tokens", 0) or 0)
        c_tokens = int(result.get("completion_tokens", 0) or 0)
        result["cost_usd"] = float(estimate_cost_usd(p_tokens, c_tokens))

        pipeline_results.append(result)

    # 4) Judge pipelines (LLM judge)
    candidates = [{"pipeline": r["pipeline_name"], "answer": r.get("answer", "")} for r in pipeline_results]
    judge_out = judge_pipelines(question, retrieved_chunks, candidates)

    # Map evaluations by pipeline name
    eval_by_pipeline: Dict[str, Dict[str, Any]] = {}
    for ev in judge_out.get("evaluations", []):
        p = ev.get("pipeline")
        if p:
            eval_by_pipeline[p] = ev

    # Merge judge scores into pipeline_results
    optimizer_debug: Dict[str, Any] = {"judge_model": judge_out.get("judge_model"), "evaluations": []}

    for r in pipeline_results:
        p = r["pipeline_name"]
        ev = eval_by_pipeline.get(p, {})
        r["quality_score"] = float(ev.get("quality_score", 0.0) or 0.0)
        r["grounded_score"] = float(ev.get("grounded_score", 0.0) or 0.0)
        r["structure_score"] = float(ev.get("structure_score", 0.0) or 0.0)
        r["judge_overall_score"] = float(ev.get("overall_score", 0.0) or 0.0)
        r["judge_flags"] = ev.get("flags", []) or []

        optimizer_debug["evaluations"].append({
            "pipeline": p,
            "quality": r["quality_score"],
            "grounded": r["grounded_score"],
            "structure": r["structure_score"],
            "overall": r["judge_overall_score"],
            "cost_usd": r["cost_usd"],
            "latency_ms": float(r.get("generation_time_ms", 0.0) or 0.0),
            "total_tokens": int(r.get("total_tokens", 0) or 0),
            "flags": r["judge_flags"],
        })

    # 5) Hallucination auto-rejection (hard constraint)
    passed = [r for r in pipeline_results if r["grounded_score"] >= MIN_GROUNDED_SCORE]

    if not passed:
        return ok({
            "doc_id": doc_id,
            "question": question,
            "answer": "Not found in the document.",
            "sources": sources,
            "metrics": {
                "model_name": None,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "generation_time_ms": 0.0,
                "cost_usd": 0.0,
                "pipeline_selected": None,
            },
            "optimizer_debug": {
                **optimizer_debug,
                "note": f"All pipelines rejected (grounded_score < {MIN_GROUNDED_SCORE}).",
            },
        }, request)

    # 6) BALANCED MODE SELECTION (quality - cost - latency), cost/latency normalized
    min_cost = min(float(r.get("cost_usd", 0.0) or 0.0) for r in passed)
    max_cost = max(float(r.get("cost_usd", 0.0) or 0.0) for r in passed)

    min_latency = min(float(r.get("generation_time_ms", 0.0) or 0.0) for r in passed)
    max_latency = max(float(r.get("generation_time_ms", 0.0) or 0.0) for r in passed)

    for r in passed:
        cost_norm = _normalize(float(r.get("cost_usd", 0.0) or 0.0), min_cost, max_cost)
        latency_norm = _normalize(float(r.get("generation_time_ms", 0.0) or 0.0), min_latency, max_latency)
        overall = float(r.get("judge_overall_score", 0.0) or 0.0)

        r["balanced_score"] = (W_QUALITY * overall) - (W_COST * cost_norm) - (W_LATENCY * latency_norm)

    best_result = max(passed, key=lambda r: r.get("balanced_score", float("-inf")))

    # Add balanced_score into optimizer_debug so you can see why it won
    for row in optimizer_debug["evaluations"]:
        if row["pipeline"] == best_result["pipeline_name"]:
            row["balanced_winner"] = True
        row["balanced_score"] = next(
            (x.get("balanced_score") for x in passed if x["pipeline_name"] == row["pipeline"]),
            None
        )

    # 7) Final metrics
    answer = best_result.get("answer", "")
    prompt_tokens = int(best_result.get("prompt_tokens", 0) or 0)
    completion_tokens = int(best_result.get("completion_tokens", 0) or 0)
    total_tokens = int(best_result.get("total_tokens", prompt_tokens + completion_tokens) or 0)
    latency_ms = float(best_result.get("generation_time_ms", 0.0) or 0.0)
    model_name = best_result.get("model_name") or "gpt-4o"
    pipeline_name = best_result.get("pipeline_name")
    cost_usd = float(best_result.get("cost_usd", 0.0) or 0.0)

    # 8) Persist QueryLog (never break response)
    try:
        log_kwargs = dict(
            doc_id=doc_id,
            question=question,
            top_k=int(top_k),
            sources=sources,
            model_name=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=latency_ms,
        )
        if hasattr(QueryLog, "cost_usd"):
            log_kwargs["cost_usd"] = float(cost_usd)

        log = QueryLog(**log_kwargs)
        db.add(log)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.exception("Failed to persist QueryLog for doc_id=%s: %s", doc_id, str(e))

    return ok({
        "doc_id": doc_id,
        "question": question,
        "answer": answer,
        "sources": sources,
        "metrics": {
            "model_name": model_name,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "generation_time_ms": latency_ms,
            "cost_usd": cost_usd,
            "pipeline_selected": pipeline_name,
            "judge_overall_score": best_result.get("judge_overall_score", None),
            "grounded_score": best_result.get("grounded_score", None),
            "balanced_score": best_result.get("balanced_score", None),
        },
        "optimizer_debug": optimizer_debug,
    }, request)


@router.get("/{doc_id}/logs")
def get_query_logs(
    request: Request,
    doc_id: str,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    _ensure_doc_exists(db, doc_id)

    logs = (
        db.query(QueryLog)
        .filter(QueryLog.doc_id == doc_id)
        .order_by(QueryLog.created_at.desc())
        .limit(limit)
        .all()
    )

    out = []
    for l in logs:
        item = {
            "id": l.id,
            "doc_id": l.doc_id,
            "question": l.question,
            "top_k": l.top_k,
            "sources": l.sources,
            "model_name": l.model_name,
            "prompt_tokens": l.prompt_tokens,
            "completion_tokens": l.completion_tokens,
            "total_tokens": l.total_tokens,
            "latency_ms": l.latency_ms,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        if hasattr(l, "cost_usd"):
            item["cost_usd"] = getattr(l, "cost_usd")
        out.append(item)

    return ok(out, request)


@router.post("/{doc_id}/cache/invalidate")
def invalidate_cache(request: Request, doc_id: str, db: Session = Depends(get_db)):
    _ensure_doc_exists(db, doc_id)
    _cache_invalidate(doc_id)
    return ok({"doc_id": doc_id}, request)