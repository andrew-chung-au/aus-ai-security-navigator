from __future__ import annotations

from dataclasses import dataclass

# Pricing last checked against Gemini Developer API pricing page on 2026-07-26.

@dataclass(frozen=True)
class ModelPricing:
    model_id: str
    input_per_million_usd: float
    output_per_million_usd: float
    notes: str = ""


MODEL_PRICING: dict[str, ModelPricing] = {
    "gemini-3.1-flash-lite": ModelPricing(
        model_id="gemini-3.1-flash-lite",
        input_per_million_usd=0.25,
        output_per_million_usd=1.50,
        notes="Gemini Developer API standard paid tier for text/image/video input.",
    ),
}


def estimate_token_cost_usd(
    model_id: str,
    prompt_tokens: int | None,
    completion_tokens: int | None,
) -> tuple[float, bool]:
    pricing = MODEL_PRICING.get(model_id.strip())
    if pricing is None:
        return 0.0, False

    prompt_tokens = prompt_tokens or 0
    completion_tokens = completion_tokens or 0

    input_cost = (prompt_tokens / 1_000_000) * pricing.input_per_million_usd
    output_cost = (completion_tokens / 1_000_000) * pricing.output_per_million_usd
    return round(input_cost + output_cost, 8), True