from domain.context import RequestContext
from graph.workflows.compare_export_workflow import build_compare_export_workflow
from graph.workflows.qa_workflow import build_qa_workflow


def test_qa_workflow_runs_end_to_end():
    ctx = RequestContext(user_id="u1", request_id="wf-qa")
    app = build_qa_workflow()
    out = app.invoke(
        {
            "user_query": "what is the contribution?",
            "context": ctx.model_dump(),
            "top_k": 2,
            "enable_judge": True,
        }
    )
    assert out.get("final_answer")
    assert out.get("evidences")
    assert out.get("retrieved_papers")
    assert out.get("working_document_ids")
    assert out.get("judge_results")
    assert out.get("trajectory_judge_result")


def test_compare_export_workflow_runs_end_to_end():
    ctx = RequestContext(user_id="u1", request_id="wf-cmp")
    app = build_compare_export_workflow()
    out = app.invoke(
        {
            "user_query": "compare these papers",
            "context": ctx.model_dump(),
            "top_k": 2,
            "enable_judge": True,
        }
    )
    assert out.get("bibtex")
    assert out["bibtex"]["export_file_uri"].startswith("file://")
    assert out.get("final_answer")
    assert out.get("retrieved_papers")
    assert out.get("working_document_ids")
    assert out.get("judge_results")
    assert out.get("trajectory_judge_result")
