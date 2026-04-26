from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from domain.judge import DimensionScore


class JudgeJsonParseError(ValueError):
    pass


class AnswerQualityLLMOutput(BaseModel):
    passed: bool
    overall_score: float
    dimension_scores: list[DimensionScore] = Field(default_factory=list)
    hallucinated_claims: list[str] = Field(default_factory=list)
    unsupported_claims: list[str] = Field(default_factory=list)
    improvement_suggestions: list[str] = Field(default_factory=list)
    judge_mode: str = "llm-json"
    fallback_reason: str | None = None


class TrajectoryJudgeLLMOutput(BaseModel):
    passed: bool
    overall_score: float
    tool_selection_score: float
    efficiency_score: float
    grounding_score: float
    failure_points: list[str] = Field(default_factory=list)
    improvement_suggestions: list[str] = Field(default_factory=list)
    judge_mode: str = "llm-json"
    fallback_reason: str | None = None


def _extract_json_text(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        parts = [p.strip() for p in text.split("```") if p.strip()]
        if parts:
            candidate = parts[0]
            if candidate.startswith("json"):
                candidate = candidate[4:].strip()
            text = candidate
    if text.startswith("{") and text.endswith("}"):
        return text
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return text[start : end + 1]
    raise JudgeJsonParseError("LLM output does not contain JSON object")


def _load_json(raw: str) -> dict[str, Any]:
    text = _extract_json_text(raw)
    try:
        loaded = json.loads(text)
    except json.JSONDecodeError as exc:
        raise JudgeJsonParseError(f"invalid judge JSON: {exc.msg}") from exc
    if not isinstance(loaded, dict):
        raise JudgeJsonParseError("judge JSON root must be an object")
    return loaded


def parse_answer_quality_json(raw: str) -> AnswerQualityLLMOutput:
    payload = _load_json(raw)
    try:
        return AnswerQualityLLMOutput.model_validate(payload)
    except Exception as exc:
        raise JudgeJsonParseError(f"answer quality schema validation failed: {exc}") from exc


def parse_trajectory_json(raw: str) -> TrajectoryJudgeLLMOutput:
    payload = _load_json(raw)
    try:
        return TrajectoryJudgeLLMOutput.model_validate(payload)
    except Exception as exc:
        raise JudgeJsonParseError(f"trajectory schema validation failed: {exc}") from exc
