from typing import List
from app.services.llm_client import client, call_with_retry


def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Takes a list of strings and returns a list of embeddings.
    Order is preserved.
    """
    response = call_with_retry(lambda: client.embeddings.create(
        model="text-embedding-3-large",
        input=texts
    ))

    return [item.embedding for item in response.data]