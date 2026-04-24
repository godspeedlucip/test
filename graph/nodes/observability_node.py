import time
import uuid
import os

from domain.context import RequestContext
from domain.judge import JudgeRubric
from domain.observability import ObservabilityEvent
from domain.runtime import ModelConfig, PromptConfig
from observability.metrics import aggregate_metrics, get_trace, list_trace_events
from tools.judge.judge_agent_trajectory import JudgeAgentTrajectoryInput, judge_agent_trajectory_tool
from tools.observability.record_observability_event import (
    RecordObservabilityEventInput,
    record_observability_event_tool,
)

from graph.nodes.common import run_node


def _default_model_config() -> dict:
    provider_mode = os.getenv("LLM_PROVIDER_MODE", "mock").lower()
    if provider_mode == "real":
        return {"provider": "openai", "model_name": os.getenv("LLM_MODEL_NAME", "gpt-4o-mini")}
    return {"provider": "mock", "model_name": "mock-judge"}


def observability_node(state: dict):
    def _impl(s: dict):
        ctx = RequestContext.model_validate(s.get("context", {"user_id": "anonymous"}))
        trace_id = s.get("trace_id") or ctx.request_id or str(uuid.uuid4())
        workflow = s.get("workflow")
        if not workflow:
            if s.get("related_work"):
                workflow = "related_work"
            elif s.get("comparison") or s.get("bibtex"):
                workflow = "compare"
            else:
                workflow = "qa"
        judge_results = list(s.get("judge_results", []))
        trajectory_result = s.get("trajectory_judge_result")

        # Reserve trajectory judge across qa / compare / related_work even when not explicitly wired as a node.
        if workflow in {"qa", "compare", "related_work"} and trajectory_result is None:
            trajectory = judge_agent_trajectory_tool.execute(
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
                    final_answer=s.get("final_answer") or s.get("answer"),
                    rubric=JudgeRubric(
                        rubric_name="trajectory_default",
                        rubric_version="v1",
                        dimensions=[
                            "correctness",
                            "grounding",
                            "citation_consistency",
                            "completeness",
                            "clarity",
                            "tool_use_efficiency",
                        ],
                    ),
                )
            )
            if trajectory.success:
                trajectory_result = trajectory.data
                trajectory_result["judge_stage"] = "trajectory"
                judge_results.append(trajectory_result)

        trace = get_trace(trace_id)
        events = list_trace_events(trace_id)
        metrics = aggregate_metrics(trace_id=trace_id)
        summary = {
            "trace_found": trace is not None,
            "event_count": len(events),
            "has_error": bool(s.get("errors")),
            "artifacts": len(s.get("artifacts", [])),
            "steps": len(s.get("execution_steps", [])),
            "checkpoints": len(s.get("checkpoints", [])),
            "request_layer": metrics.get("request_layer", {}),
            "step_layer": metrics.get("step_layer", {}),
            "quality_layer": metrics.get("quality_layer", {}),
            "cost_layer": metrics.get("cost_layer", {}),
            "total_tokens": metrics.get("total_tokens", 0),
            "estimated_cost": metrics.get("estimated_cost", 0.0),
            "judge_score": metrics.get("judge_score"),
            "tool_call_count": metrics.get("tool_call_count", 0),
            "error_count": metrics.get("error_count", 0),
        }
        event = ObservabilityEvent(
            event_type="request_finished",
            trace_id=trace_id,
            span_id=str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{trace_id}:observability:{workflow}:{int(time.time())//60}")),
            timestamp_ms=int(time.time() * 1000),
            payload={
                "success": not bool(s.get("errors")),
                "total_steps": len(s.get("execution_steps", [])),
                "errors": s.get("errors", []),
                "workflow": workflow,
                "observability_summary": summary,
            },
        )
        recorded = record_observability_event_tool.execute(RecordObservabilityEventInput(context=ctx, event=event))
        if not recorded.success:
            raise RuntimeError(recorded.error.message if recorded.error else "record_observability_event failed")
        return {
            "trajectory_judge_result": trajectory_result,
            "judge_results": judge_results,
            "observability_summary": summary,
        }

    return run_node("observability_node", state, _impl)
