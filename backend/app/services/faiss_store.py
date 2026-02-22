# backend/app/services/faiss_store.py
from __future__ import annotations

import os
from typing import List, Tuple
import numpy as np
import faiss

from app.services.vector_index import to_float32_matrix, normalize_rows

def build_faiss_index(embeddings: List[List[float]]) -> faiss.Index:
    """
    Build a FAISS index using cosine similarity.

    Trick:
    - cosine(a,b) == dot(a_norm, b_norm)
    - so we normalize vectors and use IndexFlatIP (inner product)
    """
    mat = to_float32_matrix(embeddings)
    mat = normalize_rows(mat)

    dim = mat.shape[1]
    index = faiss.IndexFlatIP(dim)   # inner product index
    index.add(mat)                   # adds N vectors
    return index

def save_index(doc_folder: str, index: faiss.Index) -> str:
    index_path = os.path.join(doc_folder, "faiss.index")
    faiss.write_index(index, index_path)
    return index_path

def load_index(doc_folder: str) -> faiss.Index:
    index_path = os.path.join(doc_folder, "faiss.index")
    if not os.path.exists(index_path):
        raise FileNotFoundError(f"FAISS index not found: {index_path}")
    return faiss.read_index(index_path)

def search_index(index: faiss.Index, query_embedding: List[float], top_k: int) -> Tuple[List[int], List[float]]:
    """
    Returns:
      indices: positions into chunks list
      scores: cosine similarity scores (higher = more similar)
    """
    q = np.array([query_embedding], dtype=np.float32)  # shape (1, d)
    q = normalize_rows(q)

    scores, idx = index.search(q, top_k)  # shapes (1, k), (1, k)
    return idx[0].tolist(), scores[0].tolist()
