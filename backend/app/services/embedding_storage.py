import json
import os
from typing import List

def save_embeddings(doc_folder: str, embeddings: List[List[float]]) -> str:
    path = os.path.join(doc_folder, "embeddings.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(embeddings, f)
    return path
