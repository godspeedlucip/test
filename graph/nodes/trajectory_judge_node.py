import os

from domain.context import RequestContext
from domain.judge import JudgeRubric
from domain.runtime import ModelConfig, PromptConfig
from observability.emitter import get_emitter
from tools.judge.judge_agent_trajectory import JudgeAgentTrajectoryInput, judge_agent_trajectory_tool

from graph.nodes.common import run_node


def _default_model_config() -> dict:
    provider_mode = os.getenv("LLM_PROVIDER_MODE", "mock").lower()
    if provider_mode == "real":
        return {"provider": "openai", "model_name": os.getenv("LLM_MODEL_NAME", "gpt-4o-mini")}
    return {"provider": "mock", "model_name": "mock-judge"}


def trajectory_judge_node(state: dict):
    def _impl(s: dict):
        ctx = RequestContext.model_validate(s.get("context", {"user_id": "anonymous"}))
        rubric = JudgeRubric.model_validate(
            {
                "rubric_name": "trajectory_default",
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
        result = judge_agent_trajectory_tool.execute(
            JudgeAgentTrajectoryInput(
                context=ctx,
                model=ModelConfig.model_validate(s.get("model") or _default_model_config()),
                prompt=PromptConfig.model_validate(
                    s.get("prompt") or {"prompt_name": "judge_agent_trajectory", "prompt_version": "v1"}
                ),
                runtime=s.get("runtime"),
                user_query=s.get("user_query", ""),
                plan=s.get("plan", []),
                execution_steps=s.get("execution_steps", []),
                final_answer=s.get("answer") or s.get("final_answer"),
                rubric=rubric,
            )
        )
        if not result.success:
            raise RuntimeError(f"judge_agent_trajectory failed: {result.error.message}")

        judge_result = result.data
        judge_result["judge_stage"] = "trajectory"
        get_emitter().emit(
            event_type="judge_finished",
            trace_id=s.get("trace_id") or ctx.request_id or "unknown",
            payload={
                "stage": "trajectory",
                "passed": judge_result.get("passed", False),
                "overall_score": judge_result.get("overall_score"),
            },
        )
        return {
            "trajectory_judge_result": judge_result,
            "judge_results": s.get("judge_results", []) + [judge_result],
        }

    return run_node("trajectory_judge_node", state, _impl)
