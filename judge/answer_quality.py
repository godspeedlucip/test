from __future__ import annotations

from pydantic import BaseModel, Field

from domain.evidence import EvidenceSpan
from domain.judge import DimensionScore, JudgeRubric
from domain.runtime import ModelConfig, PromptConfig
from integrations import resolve_prompt_config, run_llm_task
from judge.parser import AnswerQualityLLMOutput, parse_answer_quality_json


class AnswerQualityJudgeResult(BaseModel):
    passed: bool
    overall_score: float
    dimension_scores: list[DimensionScore] = Field(default_factory=list)
    hallucinated_claims: list[str] = Field(default_factory=list)
    unsupported_claims: list[str] = Field(default_factory=list)
    improvement_suggestions: list[str] = Field(default_factory=list)
    judge_mode: str = "rule"
    fallback_reason: str | None = None


class AnswerQualityJudge:
    def __init__(self) -> None:
        self.last_llm_meta: dict[str, object] = {}

    def evaluate(
        self,
        *,
        question: str,
        answer: str,
        evidences: list[EvidenceSpan],
        rubric: JudgeRubric,
        model: ModelConfig | None = None,
        prompt: PromptConfig | None = None,
    ) -> AnswerQualityJudgeResult:
        prompt_cfg = resolve_prompt_config(prompt, default_name="judge_answer_quality")
        evidence_lines = "\n".join(f"- {e.text}" for e in evidences) if evidences else "- <none>"
        body = (
            "Return strict JSON only.\n"
            "Schema keys: passed, overall_score, dimension_scores, hallucinated_claims, unsupported_claims, improvement_suggestions, judge_mode.\n"
            f"Question:\n{question}\n\n"
            f"Answer:\n{answer}\n\n"
            f"Rubric:\n{rubric.model_dump_json()}\n\n"
            f"Evidence:\n{evidence_lines}\n"
        )
        llm_result = run_llm_task(
            task_type="judge_answer_quality",
            prompt_name=prompt_cfg.prompt_name,
            prompt_version=prompt_cfg.prompt_version,
            body=body,
            requested_model=model,
            response_format="json",
        )
        self.last_llm_meta = {
            "model_name": llm_result.response.model_name,
            "prompt_name": llm_result.loaded_prompt.prompt_name,
            "prompt_version": llm_result.loaded_prompt.prompt_version,
            "token_usage": llm_result.response.token_usage,
            "estimated_cost_usd": llm_result.estimated_cost_usd,
            "latency_ms": llm_result.latency_ms,
        }
        parsed: AnswerQualityLLMOutput = parse_answer_quality_json(llm_result.response.text)
        return AnswerQualityJudgeResult.model_validate(parsed.model_dump())
