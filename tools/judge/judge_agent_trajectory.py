from __future__ import annotations

import time

from pydantic import BaseModel, Field

from domain.base import ToolMeta
from domain.context import RequestContext
from domain.judge import JudgeRubric
from domain.runtime import ModelConfig, PromptConfig, RuntimeConfig
from judge.parser import JudgeJsonParseError
from judge.trajectory import TrajectoryJudge
from observability.emitter import get_emitter
from tools.base import BaseToolHandler, failed_result, make_tool_error, success_result


class JudgeAgentTrajectoryInput(BaseModel):
    context: RequestContext
    model: ModelConfig | None = None
    prompt: PromptConfig | None = None
    runtime: RuntimeConfig | None = None
    user_query: str
    plan: list[str] = Field(default_factory=list)
    execution_steps: list[dict] = Field(default_factory=list)
    final_answer: str | None = None
    rubric: JudgeRubric


class JudgeAgentTrajectoryOutputData(BaseModel):
    passed: bool
    overall_score: float
    tool_selection_score: float
    efficiency_score: float
    grounding_score: float
    failure_points: list[str] = Field(default_factory=list)
    improvement_suggestions: list[str] = Field(default_factory=list)
    judge_mode: str = "llm-json"
    fallback_reason: str | None = None


class JudgeAgentTrajectoryHandler(BaseToolHandler):
    tool_name = "judge_agent_trajectory"
    input_model = JudgeAgentTrajectoryInput
    output_model = JudgeAgentTrajectoryOutputData

    def __init__(self) -> None:
        super().__init__()
        self.judge = TrajectoryJudge()

    def run(self, payload: JudgeAgentTrajectoryInput):
        started_ms = int(time.time() * 1000)
        try:
            result = self.judge.evaluate(
                user_query=payload.user_query,
                plan=payload.plan,
                execution_steps=payload.execution_steps,
                final_answer=payload.final_answer,
                rubric=payload.rubric,
                model=payload.model,
                prompt=payload.prompt,
            )
            duration_ms = int(time.time() * 1000) - started_ms
            llm_meta = dict(self.judge.last_llm_meta or {})
            meta = ToolMeta(
                tool_name=self.tool_name,
                model_name=str(llm_meta.get("model_name") or (payload.model.model_name if payload.model else "")) or None,
                prompt_name=str(llm_meta.get("prompt_name") or (payload.prompt.prompt_name if payload.prompt else "")) or None,
                prompt_version=str(llm_meta.get("prompt_version") or (payload.prompt.prompt_version if payload.prompt else "")) or None,
                token_usage=llm_meta.get("token_usage"),
                latency_ms=int(llm_meta.get("latency_ms") or duration_ms),
                duration_ms=duration_ms,
                estimated_cost_usd=float(llm_meta.get("estimated_cost_usd") or 0.0),
            )
            get_emitter().emit(
                event_type="judge_finished",
                trace_id=payload.context.request_id or "unknown",
                payload={
                    "judge": self.tool_name,
                    "stage": "trajectory",
                    "passed": result.passed,
                    "overall_score": result.overall_score,
                    "judge_mode": result.judge_mode,
                    "model_name": meta.model_name,
                    "prompt_version": meta.prompt_version,
                    "token_usage": meta.token_usage,
                    "duration_ms": duration_ms,
                },
            )
            return success_result(
                tool_name=self.tool_name,
                data=JudgeAgentTrajectoryOutputData.model_validate(result.model_dump()),
                meta=meta,
            )
        except JudgeJsonParseError as exc:
            get_emitter().emit(
                event_type="error_raised",
                trace_id=payload.context.request_id or "unknown",
                payload={"tool_name": self.tool_name, "error_code": "judge_json_parse_error", "error_layer": "parser"},
            )
            return failed_result(
                tool_name=self.tool_name,
                error=make_tool_error(code="judge_json_parse_error", message=str(exc), error_layer="parser"),
            )
        except Exception as exc:
            get_emitter().emit(
                event_type="error_raised",
                trace_id=payload.context.request_id or "unknown",
                payload={"tool_name": self.tool_name, "error_code": "judge_execution_failed", "error_layer": "judge"},
            )
            return failed_result(
                tool_name=self.tool_name,
                error=make_tool_error(code="judge_execution_failed", message=str(exc), error_layer="judge"),
            )


judge_agent_trajectory_tool = JudgeAgentTrajectoryHandler()
