from dataclasses import dataclass
from typing import Optional


@dataclass
class PipelineConfig:
    name: str
    top_k: int
    similarity_threshold: float
    max_output_tokens: int
    prompt_style: str  # "strict" | "explanatory"

PIPELINE_VARIANTS = [
    PipelineConfig(
        name="balanced",
        top_k=5,
        similarity_threshold=0.15,
        max_output_tokens=400,
        prompt_style="strict",
    ),
    PipelineConfig(
        name="deep_retrieval",
        top_k=8,
        similarity_threshold=0.10,
        max_output_tokens=500,
        prompt_style="strict",
    ),
    PipelineConfig(
        name="concise",
        top_k=3,
        similarity_threshold=0.20,
        max_output_tokens=250,
        prompt_style="strict",
    ),
]
