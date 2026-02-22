from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

from app.services.llm_client import client, call_with_retry

DEFAULT_JUDGE_MODEL = "gpt-4o"


def _build_context(context_chunks: List[str]) -> str:
    """
    Same format as generator: stable chunk labels.
    """
    parts = []
    for i, chunk in enumerate(context_chunks):
        parts.append(f"[chunk {i}] {chunk}")
    return "\n\n".join(parts)


def _safe_json_loads(s: str) -> Optional[dict]:
    """
    Best-effort JSON parsing.
    """
    try:
        return json.loads(s)
    except Exception:
        return None


def judge_pipelines(
    question: str,
    context_chunks: List[str],
    candidates: List[Dict[str, Any]],
    model: str = DEFAULT_JUDGE_MODEL,
    max_output_tokens: int = 600,
) -> Dict[str, Any]:
    """
    Judge multiple pipeline answers.

    candidates item format (expected):
      {
        "pipeline": "strict",
        "answer": "...",
        "latency_ms": 1234.0,
        "total_tokens": 1500,
        "cost_usd": 0.0042
      }

    Returns:
      {
        "judge_model": "...",
        "evaluations": [
            {
              "pipeline": "...",
              "quality_score": 0-10,
              "grounded_score": 0-10,
              "structure_score": 0-10,
              "overall_score": 0-10,
              "reasoning": "short",
              "flags": ["missing_citations", ...]
            }, ...
        ],
        "judge_latency_ms": ...
      }
    """

    start = time.time()
    context_text = _build_context(context_chunks)

    # Keep judge strict and deterministic in output shape
    system_msg = (
        "You are a strict evaluator for a RAG system.\n"
        "You must score answers using ONLY the provided CONTEXT.\n"
        "\n"
        "Scoring rubric (0-10 each):\n"
        "1) quality_score: correctness + completeness for the QUESTION.\n"
        "2) grounded_score: how well the answer is supported by CONTEXT; "
        "penalize any claim not clearly supported.\n"
        "3) structure_score: clarity, organization, minimal repetition; "
        "for multi-part questions expect a structured response.\n"
        "\n"
        "Rules:\n"
        "- If the answer includes claims not supported by CONTEXT, grounded_score must be low.\n"
        "- If citations like [chunk N] are missing for key claims, add flag 'missing_citations'.\n"
        "- If the answer is obviously truncated / cut off, add flag 'truncated'.\n"
        "- If the answer correctly says 'Not found in the document.' AND the context truly lacks it, that can be high groundedness.\n"
        "\n"
        "Output MUST be valid JSON only. No extra text.\n"
        "JSON schema:\n"
        "{\n"
        '  "evaluations": [\n'
        "    {\n"
        '      "pipeline": string,\n'
        '      "quality_score": number,\n'
        '      "grounded_score": number,\n'
        '      "structure_score": number,\n'
        '      "overall_score": number,\n'
        '      "reasoning": string,\n'
        '      "flags": [string, ...]\n'
        "    }\n"
        "  ]\n"
        "}\n"
    )

    # Build candidates block for the judge
    cand_lines = []
    for c in candidates:
        cand_lines.append(
            f"PIPELINE: {c.get('pipeline')}\n"
            f"ANSWER:\n{c.get('answer','')}\n"
            "----"
        )
    candidates_text = "\n\n".join(cand_lines)

    user_msg = (
        f"QUESTION:\n{question}\n\n"
        f"CONTEXT:\n{context_text}\n\n"
        f"CANDIDATES:\n{candidates_text}\n\n"
        "Return JSON exactly in the required schema."
    )

    resp = call_with_retry(lambda: client.responses.create(
    model=model,
    input=[
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ],
    max_output_tokens=max_output_tokens,
    
))

        # Extract text safely from Responses API
    raw = ""

    if hasattr(resp, "output") and resp.output:
        for item in resp.output:
            if hasattr(item, "content"):
                for part in item.content:
                    if getattr(part, "type", "") == "output_text":
                        raw += part.text

    raw = raw.strip()

    parsed = _safe_json_loads(raw)
    if not parsed or "evaluations" not in parsed or not isinstance(parsed["evaluations"], list):
        # Fail-safe: return neutral low scores if judge output is malformed
        evals = []
        for c in candidates:
            evals.append(
                {
                    "pipeline": c.get("pipeline", "unknown"),
                    "quality_score": 0,
                    "grounded_score": 0,
                    "structure_score": 0,
                    "overall_score": 0,
                    "reasoning": "Judge output malformed; defaulting to 0.",
                    "flags": ["judge_output_malformed"],
                }
            )
        parsed = {"evaluations": evals}

    # Sanitize numbers and compute overall_score if judge didn't
    for e in parsed["evaluations"]:
        for k in ["quality_score", "grounded_score", "structure_score", "overall_score"]:
            try:
                e[k] = float(e.get(k, 0))
            except Exception:
                e[k] = 0.0
        if not e.get("overall_score"):
            # conservative default if missing
            e["overall_score"] = round((e["quality_score"] + e["grounded_score"] + e["structure_score"]) / 3.0, 3)
        if "flags" not in e or not isinstance(e["flags"], list):
            e["flags"] = []

        # Keep within bounds
        for k in ["quality_score", "grounded_score", "structure_score", "overall_score"]:
            e[k] = max(0.0, min(10.0, e[k]))

        if "reasoning" not in e:
            e["reasoning"] = ""

    judge_latency_ms = (time.time() - start) * 1000.0

    return {
        "judge_model": model,
        "evaluations": parsed["evaluations"],
        "judge_latency_ms": float(judge_latency_ms),
    }
