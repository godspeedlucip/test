from domain.context import RequestContext
from domain.judge import JudgeRubric
from domain.runtime import ModelConfig, PromptConfig
from tools.judge.judge_answer_quality import JudgeAnswerQualityInput, judge_answer_quality_tool

from graph.nodes.common import run_node


def judge_node(state: dict):
    def _impl(s: dict):
        if not s.get("enable_judge", False):
            return {}
        ctx = RequestContext.model_validate(s.get("context", {"user_id": "anonymous"}))
        rubric = JudgeRubric.model_validate(
            s.get("rubric")
            or {
                "rubric_name": "default_research",
                "rubric_version": "v1",
                "dimensions": ["correctness", "grounding", "clarity"],
            }
        )
        result = judge_answer_quality_tool.execute(
            JudgeAnswerQualityInput(
                context=ctx,
                model=ModelConfig.model_validate(s.get("model") or {"provider": "mock", "model_name": "mock-judge"}),
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
            return {"errors": s.get("errors", []) + [result.error.message]}
        return {"judge_results": s.get("judge_results", []) + [result.data]}

    return run_node("judge_node", state, _impl)
