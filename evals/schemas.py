from pydantic import BaseModel, Field

from domain.context import RequestContext
from domain.runtime import ModelConfig, PromptConfig, RuntimeConfig


class EvalRunInput(BaseModel):
    context: RequestContext
    dataset_name: str
    dataset_version: str
    target_tool: str
    model: ModelConfig
    prompt: PromptConfig
    runtime: RuntimeConfig | None = None
    max_samples: int | None = None


class EvalRunOutputData(BaseModel):
    run_id: str
    total_samples: int
    completed_samples: int
    metrics: dict[str, float] = Field(default_factory=dict)
