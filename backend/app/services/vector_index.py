# backend/app/services/vector_index.py
from __future__ import annotations

from typing import List, Tuple
import numpy as np

def to_float32_matrix(vectors: List[List[float]]) -> np.ndarray:
    """
    Convert Python list of vectors -> numpy float32 matrix of shape (n, d).
    """
    mat = np.array(vectors, dtype=np.float32)
    if mat.ndim != 2:
        raise ValueError(f"Expected 2D matrix, got shape {mat.shape}")
    return mat

def normalize_rows(mat: np.ndarray) -> np.ndarray:
    """
    Normalize each row vector to unit length so inner product == cosine similarity.
    """
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms = np.clip(norms, 1e-12, None)
    return mat / norms
