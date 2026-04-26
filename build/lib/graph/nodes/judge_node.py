import os

from domain.context import RequestContext
from domain.judge import JudgeRubric
from domain.runtime import ModelConfig, PromptConfig
from observability.emitter import get_emitter
from tools.judge.judge_answer_quality import JudgeAnswerQualityInput, judge_answer_quality_tool

from graph.nodes.common import run_node


def _default_model_config() -> dict:
    provider_mode = os.getenv("LLM_PROVIDER_MODE", "mock").lower()
    if provider_mode == "real":
        return {"provider": "openai", "model_name": os.getenv("LLM_MODEL_NAME", "gpt-4o-mini")}
    return {"provider": "mock", "model_name": "mock-judge"}


def judge_node(state: dict):
    def _impl(s: dict):
        workflow = s.get("workflow")
        trajectory_reserved = workflow in {"qa", "compare", "related_work"}
        if not s.get("enable_judge", False):
            default_route = "trajectory_judge" if workflow == "related_work" else "proceed"
            return {"route_after_judge": default_route, "trajectory_judge_reserved": trajectory_reserved}

        ctx = RequestContext.model_validate(s.get("context", {"user_id": "anonymous"}))
        rubric = JudgeRubric.model_validate(
            s.get("rubric")
            or {
                "rubric_name": "default_research",
                "rubric_version": "v1",
                "dimensions": [
                    "correctness",
                    "grounding",
                    "citation_consistency",
                    "completeness",
                    "clarity",
                    "tool_use_efficiency",
                ],
            }
        )

        result = judge_answer_quality_tool.execute(
            JudgeAnswerQualityInput(
                context=ctx,
                model=ModelConfig.model_validate(s.get("model") or _default_model_config()),
                prompt=PromptConfig.model_validate(
                    s.get("prompt") or {"prompt_name": "judge_answer_quality", "prompt_version": "v1"}
                ),
                question=s.get("question") or s.get("user_query", ""),
                answer=s.get("answer", ""),
                evidences=s.get("evidences", []),
                rubric=rubric,
            )
        )
        if not result.success:
            raise RuntimeError(f"judge_answer_quality failed: {result.error.message}")

        judge_result = result.data
        judge_result["judge_stage"] = "answer_quality"
        get_emitter().emit(
            event_type="judge_finished",
            trace_id=s.get("trace_id") or ctx.request_id or "unknown",
            payload={
                "stage": "answer_quality",
                "passed": judge_result.get("passed", False),
                "overall_score": judge_result.get("overall_score"),
                "rubric": rubric.rubric_name,
                "model_name": (result.meta.model_name if result.meta else None),
                "prompt_version": (result.meta.prompt_version if result.meta else None),
                "token_usage": (result.meta.token_usage if result.meta else None),
                "duration_ms": (result.meta.duration_ms if result.meta else None),
            },
        )

        passed = bool(judge_result.get("passed"))
        revise_count = int(s.get("revise_count", 0))
        max_revise = int(s.get("max_revise", 1))
        if workflow == "related_work":
            if passed:
                route = "trajectory_judge"
            elif revise_count < max_revise:
                route = "revise"
            else:
                route = "human_review"
        else:
            route = "proceed" if passed else "human_review"

        return {
            "judge_results": s.get("judge_results", []) + [judge_result],
            "route_after_judge": route,
            "trajectory_judge_reserved": trajectory_reserved,
        }

    return run_node("judge_node", state, _impl)
