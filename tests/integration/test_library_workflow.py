from domain.context import RequestContext
from graph.workflows.library_workflow import build_library_workflow
from integrations import get_repo


def test_library_workflow_success_path():
    ctx = RequestContext(user_id="u-lib-1", request_id="wf-lib-success")
    app = build_library_workflow()
    out = app.invoke(
        {
            "workflow": "library_save",
            "query": "transformer benchmark",
            "context": ctx.model_dump(),
            "top_k": 3,
        }
    )
    assert out.get("selected_paper_id")
    assert out.get("saved_paper_id")
    assert out.get("save_result", {}).get("saved") is True
    assert out.get("final_answer")


def test_library_workflow_duplicate_save_is_idempotent():
    ctx = RequestContext(user_id="u-lib-2", request_id="wf-lib-idempotent")
    app = build_library_workflow()

    first = app.invoke(
        {
            "workflow": "library_save",
            "query": "graph neural networks",
            "context": ctx.model_dump(),
            "top_k": 2,
        }
    )
    selected = first.get("selected_paper_id")
    second = app.invoke(
        {
            "workflow": "library_save",
            "query": "graph neural networks",
            "context": ctx.model_dump(),
            "paper_id": selected,
            "top_k": 2,
        }
    )

    library = get_repo().library.get(ctx.user_id, [])
    assert selected in library
    assert len([x for x in library if x == selected]) == 1
    assert second.get("save_result", {}).get("saved") is True


def test_library_workflow_failure_when_explicit_paper_not_found():
    ctx = RequestContext(user_id="u-lib-3", request_id="wf-lib-fail")
    app = build_library_workflow()
    out = app.invoke(
        {
            "workflow": "library_save",
            "query": "large language models",
            "paper_id": "paper-not-in-candidates",
            "context": ctx.model_dump(),
            "top_k": 2,
        }
    )
    assert out.get("errors")
