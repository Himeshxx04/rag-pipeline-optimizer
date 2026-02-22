from typing import List


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """
    Splits text into overlapping character chunks safely.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    if overlap < 0:
        raise ValueError("overlap must be >= 0")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    chunks: List[str] = []
    n = len(text)
    step = chunk_size - overlap  # how much we move forward each time

    start = 0
    while start < n:
        end = min(start + chunk_size, n)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end == n:  # ✅ reached the end, stop
            break

        start += step  # ✅ always moves forward

        if len(chunks) > 10000:
         raise RuntimeError("Too many chunks generated. Check chunking parameters.")


    return chunks
