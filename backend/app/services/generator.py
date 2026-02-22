from __future__ import annotations

import time
from typing import List, Dict, Any

from app.services.llm_client import client, call_with_retry

DEFAULT_MODEL = "gpt-4o"


# -----------------------------------------------------------------------------
# Context Builder
# -----------------------------------------------------------------------------
def _build_context(context_chunks: List[str]) -> str:
    """
    Wrap chunks with stable labels so the model can cite them.
    Example:
      [chunk 0] ...
      [chunk 1] ...
    """
    parts = []
    for i, chunk in enumerate(context_chunks):
        parts.append(f"[chunk {i}] {chunk}")
    return "\n\n".join(parts)


# -----------------------------------------------------------------------------
# System Prompts for Different Pipelines
# -----------------------------------------------------------------------------
PIPELINE_SYSTEM_PROMPTS = {

    # Your current strict pipeline (default)
    "strict": (
        "You are a document question-answering assistant.\n"
        "RULES (must follow):\n"
        "1) Use ONLY the provided context.\n"
        "2) If the answer is not explicitly in the context, reply exactly: Not found in the document.\n"
        "3) Do NOT use outside knowledge.\n"
        "4) If you answer, include chunk citations like [chunk 0], [chunk 2] for each claim.\n"
        "5) Keep the answer short and factual.\n"
    ),

    # More explanation-heavy but still grounded
    "citations_strict": (
        "You are a document QA assistant.\n"
        "RULES:\n"
        "1) Use ONLY the provided context.\n"
        "2) If answer not found, reply exactly: Not found in the document.\n"
        "3) Always include citations like [chunk 0].\n"
        "4) Provide structured explanation if multiple concepts are involved.\n"
        "5) Avoid repetition.\n"
    ),

    # Slightly more explanatory pipeline
    "explanatory": (
        "You are a document QA assistant.\n"
        "RULES:\n"
        "1) Use ONLY provided context.\n"
        "2) If missing, reply exactly: Not found in the document.\n"
        "3) Include citations.\n"
        "4) Explain clearly with examples if present in context.\n"
        "5) Structure answer using headings if needed.\n"
    ),
}


# -----------------------------------------------------------------------------
# Main Generator
# -----------------------------------------------------------------------------
def generate_answer(
    question: str,
    context_chunks: List[str],
    model: str = DEFAULT_MODEL,
    pipeline: str = "strict",
) -> Dict[str, Any]:
    """
    Multi-pipeline RAG generator.

    Pipelines:
        - strict
        - citations_strict
        - explanatory
    """

    start = time.time()

    if pipeline not in PIPELINE_SYSTEM_PROMPTS:
        pipeline = "strict"

    system_msg = PIPELINE_SYSTEM_PROMPTS[pipeline]

    context_text = _build_context(context_chunks)

    user_msg = (
        f"QUESTION:\n{question}\n\n"
        f"CONTEXT:\n{context_text}"
    )

    resp = call_with_retry(lambda: client.responses.create(
    model=model,
    input=[
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ],
    max_output_tokens=800,
))

    answer = resp.output_text.strip()

    prompt_tokens = getattr(resp.usage, "input_tokens", None) or 0
    completion_tokens = getattr(resp.usage, "output_tokens", None) or 0
    total_tokens = getattr(resp.usage, "total_tokens", None) or (prompt_tokens + completion_tokens)

    latency_ms = (time.time() - start) * 1000

    return {
        "answer": answer,
        "model_name": model,
        "pipeline_name": pipeline,  # important for optimizer phase
        "prompt_tokens": int(prompt_tokens),
        "completion_tokens": int(completion_tokens),
        "total_tokens": int(total_tokens),
        "generation_time_ms": float(latency_ms),
    }
