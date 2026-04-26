from __future__ import annotations

import time
from dataclasses import dataclass

from domain.runtime import ModelConfig, PromptConfig
from integrations.llm_client import LLMResponse, get_llm_client
from integrations.model_router import ResolvedModelRoute, get_model_router
from integrations.prompt_registry import LoadedPrompt, get_prompt_registry


@dataclass
class LLMRuntimeResult:
    response: LLMResponse
    route: ResolvedModelRoute
    loaded_prompt: LoadedPrompt
    rendered_prompt: str
    latency_ms: int
    estimated_cost_usd: float


def _normalize_token_usage(raw: dict[str, int] | None) -> dict[str, int]:
    usage = dict(raw or {})
    usage.setdefault("prompt_tokens", 0)
    usage.setdefault("completion_tokens", 0)
    usage.setdefault("total_tokens", usage["prompt_tokens"] + usage["completion_tokens"])
    return usage


_MODEL_COST_PER_1K_TOKENS_USD: dict[str, float] = {
    "mock-llm-v1": 0.0002,
    "mock-llm-fallback-v1": 0.00025,
    "mock-judge-v1": 0.00015,
    "mock-judge-v2": 0.00018,
}


def _estimate_cost_usd(model_name: str, usage: dict[str, int]) -> float:
    rate = _MODEL_COST_PER_1K_TOKENS_USD.get(model_name, 0.0002)
    total_tokens = int(usage.get("total_tokens", 0) or 0)
    return round((total_tokens / 1000.0) * rate, 8)


def run_llm_task(
    *,
    task_type: str,
    prompt_name: str,
    prompt_version: str | None,
    body: str,
    requested_model: ModelConfig | dict | None = None,
    response_format: str = "text",
) -> LLMRuntimeResult:
    model_cfg = ModelConfig.model_validate(requested_model) if requested_model is not None else None
    loaded_prompt = get_prompt_registry().load(prompt_name, prompt_version)
    route = get_model_router().resolve(task_type=task_type, requested_model=model_cfg)
    rendered_prompt = f"{loaded_prompt.text.strip()}\n\n{body.strip()}".strip()
    started = int(time.time() * 1000)
    response = get_llm_client().answer_with_fallback(
        prompt=rendered_prompt,
        primary_model=route.primary.model_name,
        fallback_models=[m.model_name for m in route.fallbacks] if route.fallback_enabled else [],
        response_format=response_format,
    )
    response.token_usage = _normalize_token_usage(response.token_usage)
    estimated_cost = _estimate_cost_usd(response.model_name, response.token_usage)
    response.token_usage["estimated_cost_microusd"] = int(estimated_cost * 1_000_000)
    latency_ms = int(time.time() * 1000) - started
    return LLMRuntimeResult(
        response=response,
        route=route,
        loaded_prompt=loaded_prompt,
        rendered_prompt=rendered_prompt,
        latency_ms=latency_ms,
        estimated_cost_usd=estimated_cost,
    )


def resolve_prompt_config(task_prompt: PromptConfig | None, *, default_name: str, default_version: str | None = None) -> PromptConfig:
    registry = get_prompt_registry()
    if task_prompt is not None:
        loaded = registry.load(task_prompt.prompt_name, task_prompt.prompt_version)
        return PromptConfig(prompt_name=loaded.prompt_name, prompt_version=loaded.prompt_version)
    loaded = registry.load(default_name, default_version)
    return PromptConfig(prompt_name=loaded.prompt_name, prompt_version=loaded.prompt_version)
