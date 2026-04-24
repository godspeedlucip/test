from domain.context import RequestContext
from graph.workflows.compare_export_workflow import build_compare_export_workflow
from graph.workflows.library_workflow import build_library_workflow
from graph.workflows.qa_workflow import build_qa_workflow


def test_qa_workflow_invokes_search_node_when_paper_ids_missing(monkeypatch):
    import graph.nodes.search_node as search_module

    called = {"search": 0}
    original_search = search_module.search_papers_tool.execute

    def wrapped_search(payload):
        called["search"] += 1
        return original_search(payload)

    monkeypatch.setattr(search_module.search_papers_tool, "execute", wrapped_search)

    app = build_qa_workflow()
    out = app.invoke(
        {
            "workflow": "qa",
            "user_query": "Please find and summarize the paper on retrieval augmentation",
            "context": RequestContext(user_id="u1", request_id="wf-tool-qa").model_dump(),
            "enable_judge": False,
            "top_k": 2,
        }
    )
    assert out.get("final_answer")
    assert called["search"] >= 1


def test_compare_workflow_calls_format_references(monkeypatch):
    import graph.nodes.compose_node as compose_module

    called = {"format_refs": 0}
    original = compose_module.format_references_tool.execute

    def wrapped(payload):
        called["format_refs"] += 1
        return original(payload)

    monkeypatch.setattr(compose_module.format_references_tool, "execute", wrapped)

    ctx = RequestContext(user_id="u1", request_id="wf-tool-cmp")
    app = build_compare_export_workflow()
    out = app.invoke(
        {
            "workflow": "compare",
            "user_query": "compare these papers",
            "context": ctx.model_dump(),
            "enable_judge": False,
            "top_k": 2,
        }
    )
    assert out.get("final_answer")
    assert called["format_refs"] >= 1


def test_library_workflow_invokes_search_node_when_query_provided(monkeypatch):
    import graph.nodes.search_node as search_module

    called = {"search": 0}
    original_search = search_module.search_papers_tool.execute

    def wrapped_search(payload):
        called["search"] += 1
        return original_search(payload)

    monkeypatch.setattr(search_module.search_papers_tool, "execute", wrapped_search)
    out = build_library_workflow().invoke(
        {
            "workflow": "library_save",
            "query": "benchmarking llm agents",
            "context": RequestContext(user_id="u-lib", request_id="wf-lib-search").model_dump(),
            "top_k": 3,
        }
    )
    assert out.get("saved_paper_id")
    assert called["search"] >= 1
