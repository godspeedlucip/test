from domain.context import RequestContext
from domain.document import DocumentAnchor
from domain.evidence import EvidenceSpan
from domain.judge import JudgeRubric
from domain.runtime import ModelConfig, PromptConfig
from observability.recorder import get_recorder
from tools.judge.judge_answer_quality import JudgeAnswerQualityInput, judge_answer_quality_tool
from tools.judge.judge_agent_trajectory import JudgeAgentTrajectoryInput, judge_agent_trajectory_tool


def test_judge_answer_quality_parses_llm_json_and_emits_event():
    ctx = RequestContext(user_id="u1", request_id="judge-json-qa")
    result = judge_answer_quality_tool.execute(
        JudgeAnswerQualityInput(
            context=ctx,
            model=ModelConfig(provider="mock", model_name="mock-judge-v1"),
            prompt=PromptConfig(prompt_name="judge_answer_quality", prompt_version="v1"),
            question="What is contribution?",
            answer="The paper contributes a method with evidence [1].",
            evidences=[
                EvidenceSpan(
                    text="method evidence",
                    anchor=DocumentAnchor(document_id="d1", chunk_id="c1", page_no=1),
                )
            ],
            rubric=JudgeRubric(rubric_name="default", rubric_version="v1", dimensions=["correctness", "grounding"]),
        )
    )
    assert result.success
    assert result.data["judge_mode"] == "llm-json"
    assert any(e.event_type == "judge_finished" and e.trace_id == "judge-json-qa" for e in get_recorder().events)


def test_judge_answer_quality_fallback_on_invalid_json():
    ctx = RequestContext(user_id="u1", request_id="judge-json-fallback")
    result = judge_answer_quality_tool.execute(
        JudgeAnswerQualityInput(
            context=ctx,
            model=ModelConfig(provider="mock", model_name="mock-judge-v1"),
            prompt=PromptConfig(prompt_name="judge_answer_quality", prompt_version="v1"),
            question="force_invalid_json",
            answer="force_invalid_json",
            evidences=[],
            rubric=JudgeRubric(rubric_name="default", rubric_version="v1", dimensions=["grounding"]),
        )
    )
    assert not result.success
    assert result.error is not None
    assert result.error.error_layer == "parser"


def test_judge_trajectory_parses_llm_json():
    ctx = RequestContext(user_id="u1", request_id="judge-json-traj")
    result = judge_agent_trajectory_tool.execute(
        JudgeAgentTrajectoryInput(
            context=ctx,
            model=ModelConfig(provider="mock", model_name="mock-judge-v1"),
            prompt=PromptConfig(prompt_name="judge_agent_trajectory", prompt_version="v1"),
            user_query="compare papers",
            plan=["prepare_documents", "compare_node"],
            execution_steps=[{"node_name": "prepare_documents", "status": "succeeded"}],
            final_answer="With evidence [1], the comparison is grounded.",
            rubric=JudgeRubric(rubric_name="traj", rubric_version="v1", dimensions=[]),
        )
    )
    assert result.success
    assert result.data["judge_mode"] == "llm-json"
