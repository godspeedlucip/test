from domain.context import RequestContext
from graph.workflows.compare_export_workflow import build_compare_export_workflow
from graph.workflows.qa_workflow import build_qa_workflow
from integrations import get_java_client
from tools.academic.search_papers import SearchPapersInput, search_papers_tool


def test_workflow_updates_java_task_status_on_success():
    ctx = RequestContext(user_id="u1", request_id="java-status-success")
    pid = search_papers_tool.execute(SearchPapersInput(context=ctx, query="llm", top_k=1)).data["papers"][0]["paper_id"]
    app = build_qa_workflow()
    out = app.invoke(
        {
            "workflow": "qa",
            "user_query": "what is contribution",
            "context": ctx.model_dump(),
            "paper_ids": [pid],
            "enable_judge": False,
        }
    )
    assert out.get("final_answer")
    assert get_java_client().task_status.get("java-status-success") in {"succeeded", "partial", "running", "started"}


def test_workflow_records_artifact_to_java_client():
    ctx = RequestContext(user_id="u1", request_id="java-artifact-success")
    pids = [
        x["paper_id"]
        for x in search_papers_tool.execute(SearchPapersInput(context=ctx, query="transformer", top_k=2)).data["papers"][:2]
    ]
    app = build_compare_export_workflow()
    out = app.invoke(
        {
            "workflow": "compare",
            "user_query": "compare and export",
            "context": ctx.model_dump(),
            "paper_ids": pids,
            "enable_judge": False,
        }
    )
    assert out.get("bibtex")
    artifacts = get_java_client().artifacts
    assert artifacts
