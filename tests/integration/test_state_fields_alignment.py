from domain.context import RequestContext
from graph.workflows.qa_workflow import build_qa_workflow


def test_workflow_updates_core_state_fields():
    ctx = RequestContext(user_id="u-state", request_id="wf-state-1")
    out = build_qa_workflow().invoke(
        {
            "workflow": "qa",
            "user_query": "summarize the main contribution",
            "context": ctx.model_dump(),
            "enable_judge": True,
            "top_k": 2,
        }
    )
    assert out.get("trace_id")
    assert out.get("execution_steps")
    assert out.get("retrieved_papers")
    assert out.get("working_document_ids")
    assert out.get("evidences")
    assert out.get("judge_results")
    assert out.get("artifacts")
