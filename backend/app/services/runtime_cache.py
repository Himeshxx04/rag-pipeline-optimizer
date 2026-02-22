# app/services/runtime_cache.py
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

@dataclass
class CacheEntry:
    chunks: Any
    index: Any
    updated_at: float
    last_access: float
    folder_mtime: float

class RuntimeCache:
    """
    Very small in-memory cache:
    - Key = doc_id
    - Value = chunks + faiss index
    """
    def __init__(self, max_docs: int = 32, ttl_seconds: int = 1800):
        self.max_docs = max_docs
        self.ttl_seconds = ttl_seconds
        self._store: Dict[str, CacheEntry] = {}

    def _evict_if_needed(self):
        if len(self._store) <= self.max_docs:
            return
        # evict least recently accessed
        victim = min(self._store.items(), key=lambda kv: kv[1].last_access)[0]
        self._store.pop(victim, None)

    def _is_expired(self, entry: CacheEntry) -> bool:
        return (time.time() - entry.updated_at) > self.ttl_seconds

    def get(self, doc_id: str, doc_folder: str) -> Optional[Tuple[Any, Any]]:
        entry = self._store.get(doc_id)
        if not entry:
            return None

        # TTL expiry
        if self._is_expired(entry):
            self._store.pop(doc_id, None)
            return None

        # folder modification check (cache invalidation)
        try:
            current_mtime = os.path.getmtime(doc_folder)
        except FileNotFoundError:
            self._store.pop(doc_id, None)
            return None

        if current_mtime != entry.folder_mtime:
            self._store.pop(doc_id, None)
            return None

        entry.last_access = time.time()
        return entry.chunks, entry.index

    def set(self, doc_id: str, doc_folder: str, chunks: Any, index: Any):
        folder_mtime = os.path.getmtime(doc_folder)
        now = time.time()
        self._store[doc_id] = CacheEntry(
            chunks=chunks,
            index=index,
            updated_at=now,
            last_access=now,
            folder_mtime=folder_mtime,
        )
        self._evict_if_needed()

    def invalidate(self, doc_id: str):
        self._store.pop(doc_id, None)

# single global cache instance
runtime_cache = RuntimeCache(max_docs=32, ttl_seconds=1800)
