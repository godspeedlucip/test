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


def run_llm_task(
    *,
    task_type: str,
    prompt_name: str,
    prompt_version: str | None,
    body: str,
    requested_model: ModelConfig | dict | None = None,
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
    )
    latency_ms = int(time.time() * 1000) - started
    return LLMRuntimeResult(
        response=response,
        route=route,
        loaded_prompt=loaded_prompt,
        rendered_prompt=rendered_prompt,
        latency_ms=latency_ms,
    )


def resolve_prompt_config(task_prompt: PromptConfig | None, *, default_name: str, default_version: str | None = None) -> PromptConfig:
    registry = get_prompt_registry()
    if task_prompt is not None:
        loaded = registry.load(task_prompt.prompt_name, task_prompt.prompt_version)
        return PromptConfig(prompt_name=loaded.prompt_name, prompt_version=loaded.prompt_version)
    loaded = registry.load(default_name, default_version)
    return PromptConfig(prompt_name=loaded.prompt_name, prompt_version=loaded.prompt_version)
