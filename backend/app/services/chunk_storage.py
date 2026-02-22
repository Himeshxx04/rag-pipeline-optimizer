import os
import json
from typing import List, Dict, Any

def save_chunks(doc_folder: str, chunks: List[Dict[str, Any]]) -> str:
    path = os.path.join(doc_folder, "chunks.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    return path

def load_chunks(doc_folder: str):
    path = os.path.join(doc_folder, "chunks.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
