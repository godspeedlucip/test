from __future__ import annotations

from dataclasses import dataclass
import os

from domain.runtime import ModelConfig, ModelRoutingPolicy


@dataclass
class ResolvedModelRoute:
    task_type: str
    primary: ModelConfig
    fallbacks: list[ModelConfig]
    fallback_enabled: bool


class InMemoryModelRouter:
    def __init__(self) -> None:
        self._policies: dict[str, ModelRoutingPolicy] = {
            "ask_paper": ModelRoutingPolicy(
                task_type="ask_paper",
                primary_model="mock-llm-v1",
                fallback_models=[],
                enable_fallback=False,
            ),
            "generate_related_work": ModelRoutingPolicy(
                task_type="generate_related_work",
                primary_model="mock-llm-v1",
                fallback_models=[],
                enable_fallback=False,
            ),
            "extract_paper_facts": ModelRoutingPolicy(
                task_type="extract_paper_facts",
                primary_model="mock-llm-v1",
                fallback_models=[],
                enable_fallback=False,
            ),
            "compare_papers": ModelRoutingPolicy(
                task_type="compare_papers",
                primary_model="mock-llm-v1",
                fallback_models=[],
                enable_fallback=False,
            ),
            "revise_related_work": ModelRoutingPolicy(
                task_type="revise_related_work",
                primary_model="mock-llm-v1",
                fallback_models=[],
                enable_fallback=False,
            ),
            "judge_answer_quality": ModelRoutingPolicy(
                task_type="judge_answer_quality",
                primary_model="mock-judge-v1",
                fallback_models=[],
                enable_fallback=False,
            ),
            "judge_agent_trajectory": ModelRoutingPolicy(
                task_type="judge_agent_trajectory",
                primary_model="mock-judge-v1",
                fallback_models=[],
                enable_fallback=False,
            ),
        }

    def set_policy(self, policy: ModelRoutingPolicy) -> None:
        self._policies[policy.task_type] = policy

    def get_policy(self, task_type: str) -> ModelRoutingPolicy | None:
        return self._policies.get(task_type)

    def list_policies(self) -> dict[str, ModelRoutingPolicy]:
        return dict(self._policies)

    def resolve(self, *, task_type: str, requested_model: ModelConfig | None = None) -> ResolvedModelRoute:
        provider_mode = os.getenv("LLM_PROVIDER_MODE", "mock").lower()
        default_provider = "openai" if provider_mode == "real" else "mock"
        default_model_name = os.getenv("LLM_MODEL_NAME", "gpt-4o-mini") if provider_mode == "real" else "mock-llm-v1"
        policy = self._policies.get(task_type)
        if requested_model is not None:
            primary = requested_model
            fallbacks: list[ModelConfig] = []
            fallback_enabled = False
            if policy and policy.enable_fallback:
                for name in policy.fallback_models:
                    if name != primary.model_name:
                        fallbacks.append(ModelConfig(provider=primary.provider, model_name=name))
            return ResolvedModelRoute(task_type=task_type, primary=primary, fallbacks=fallbacks, fallback_enabled=fallback_enabled)

        if policy is None:
            primary = ModelConfig(provider=default_provider, model_name=default_model_name)
            return ResolvedModelRoute(task_type=task_type, primary=primary, fallbacks=[], fallback_enabled=False)

        chosen_primary_name = default_model_name if provider_mode == "real" else policy.primary_model
        primary = ModelConfig(provider=default_provider, model_name=chosen_primary_name)
        fallbacks = [
            ModelConfig(provider=default_provider, model_name=name)
            for name in policy.fallback_models
            if name != chosen_primary_name
        ]
        return ResolvedModelRoute(
            task_type=task_type,
            primary=primary,
            fallbacks=fallbacks,
            fallback_enabled=policy.enable_fallback,
        )


model_router = InMemoryModelRouter()


def get_model_router() -> InMemoryModelRouter:
    return model_router
