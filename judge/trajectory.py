from __future__ import annotations

from pydantic import BaseModel, Field

from domain.judge import JudgeRubric
from domain.runtime import ModelConfig, PromptConfig
from integrations import resolve_prompt_config, run_llm_task
from judge.parser import TrajectoryJudgeLLMOutput, parse_trajectory_json


class TrajectoryJudgeResult(BaseModel):
    passed: bool
    overall_score: float
    tool_selection_score: float
    efficiency_score: float
    grounding_score: float
    failure_points: list[str] = Field(default_factory=list)
    improvement_suggestions: list[str] = Field(default_factory=list)
    judge_mode: str = "rule"
    fallback_reason: str | None = None


class TrajectoryJudge:
    def __init__(self) -> None:
        self.last_llm_meta: dict[str, object] = {}

    def evaluate(
        self,
        *,
        user_query: str,
        plan: list[str],
        execution_steps: list[dict],
        final_answer: str | None,
        rubric: JudgeRubric,
        model: ModelConfig | None = None,
        prompt: PromptConfig | None = None,
    ) -> TrajectoryJudgeResult:
        prompt_cfg = resolve_prompt_config(prompt, default_name="judge_agent_trajectory")
        body = (
            "Return strict JSON only.\n"
            "Schema keys: passed, overall_score, tool_selection_score, efficiency_score, grounding_score, failure_points, improvement_suggestions, judge_mode.\n"
            f"User Query:\n{user_query}\n\n"
            f"Plan:\n{plan}\n\n"
            f"Execution Steps:\n{execution_steps}\n\n"
            f"Final Answer:\n{final_answer or ''}\n\n"
            f"Rubric:\n{rubric.model_dump_json()}\n"
        )
        llm_result = run_llm_task(
            task_type="judge_agent_trajectory",
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
        parsed: TrajectoryJudgeLLMOutput = parse_trajectory_json(llm_result.response.text)
        return TrajectoryJudgeResult.model_validate(parsed.model_dump())
