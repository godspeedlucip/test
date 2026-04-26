from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class JudgeRubric(BaseModel):
    rubric_name: str
    rubric_version: str
    dimensions: list[str] = Field(default_factory=list)


class DimensionScore(BaseModel):
    name: str
    score: float
    reason: str | None = None


class EvalSample(BaseModel):
    sample_id: str
    task_type: str
    input_payload: dict[str, Any]
    expected_output: dict[str, Any] | None = None
    labels: dict[str, Any] = Field(default_factory=dict)
