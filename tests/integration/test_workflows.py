from graph.workflows.compare_export_workflow import build_compare_export_workflow
from graph.workflows.qa_workflow import build_qa_workflow
from tools.academic.search_papers import SearchPapersInput, search_papers_tool
from domain.context import RequestContext


def test_qa_workflow_runs_end_to_end():
    ctx = RequestContext(user_id="u1", request_id="wf-qa")
    sr = search_papers_tool.execute(SearchPapersInput(context=ctx, query="llm"))
    pid = sr.data["papers"][0]["paper_id"]

    app = build_qa_workflow()
    out = app.invoke(
        {
            "user_query": "what is the contribution?",
            "context": ctx.model_dump(),
            "paper_ids": [pid],
            "enable_judge": True,
        }
    )
    assert out.get("final_answer")


def test_compare_export_workflow_runs_end_to_end():
    ctx = RequestContext(user_id="u1", request_id="wf-cmp")
    sr = search_papers_tool.execute(SearchPapersInput(context=ctx, query="transformer", top_k=2))
    pids = [x["paper_id"] for x in sr.data["papers"][:2]]

    app = build_compare_export_workflow()
    out = app.invoke(
        {
            "user_query": "compare these papers",
            "context": ctx.model_dump(),
            "paper_ids": pids,
            "enable_judge": True,
        }
    )
    assert out.get("bibtex")
    assert out.get("final_answer")
