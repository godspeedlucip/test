from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class ModelConfig(BaseModel):
    provider: str = "mock"
    model_name: str = "mock-llm-v1"
    temperature: float = 0.2
    max_tokens: int | None = None
    top_p: float | None = None
    timeout_seconds: int = 60


class PromptConfig(BaseModel):
    prompt_name: str = "default"
    prompt_version: str = "v1"
    prompt_template_id: str | None = None
    system_prompt_ref: str | None = None
    fewshot_set_ref: str | None = None


class RuntimeConfig(BaseModel):
    environment: Literal["local", "dev", "staging", "prod"] = "dev"
    release_version: str | None = None
    experiment_bucket: str | None = None
    enable_cache: bool = True
    enable_judge: bool = False
    max_retries: int = 2


class PromptVersionSpec(BaseModel):
    prompt_name: str
    version: str
    owner: str | None = None
    change_log: str | None = None
    status: Literal["draft", "active", "deprecated"] = "active"


class ModelRoutingPolicy(BaseModel):
    task_type: str
    primary_model: str
    fallback_models: list[str] = []
    enable_fallback: bool = True
