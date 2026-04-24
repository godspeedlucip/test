from domain.context import RequestContext
from graph.workflows.library_manage_workflow import build_library_manage_workflow


def test_library_manage_save_action_runs_search_then_save():
    ctx = RequestContext(user_id="u-lib-m1", request_id="wf-lib-manage-1")
    app = build_library_manage_workflow()
    out = app.invoke(
        {
            "workflow": "library_manage",
            "action": "save",
            "query": "retrieval augmentation",
            "context": ctx.model_dump(),
            "idempotency_key": "idem-save-1",
            "top_k": 3,
        }
    )
    assert out.get("saved_paper_id")
    assert out.get("library_paper_ids")
    assert out.get("final_answer")


def test_library_manage_add_note_tag_and_list_actions():
    ctx = RequestContext(user_id="u-lib-m2", request_id="wf-lib-manage-2")
    app = build_library_manage_workflow()

    saved = app.invoke(
        {
            "workflow": "library_manage",
            "action": "save",
            "query": "agent observability",
            "context": ctx.model_dump(),
            "idempotency_key": "idem-save-2",
            "top_k": 2,
        }
    )
    paper_id = saved.get("saved_paper_id")
    assert paper_id

    noted = app.invoke(
        {
            "workflow": "library_manage",
            "action": "add_note",
            "paper_id": paper_id,
            "library_note": "use for related work",
            "context": ctx.model_dump(),
            "idempotency_key": "idem-note-2",
        }
    )
    assert noted.get("note_result", {}).get("added") is True

    tagged = app.invoke(
        {
            "workflow": "library_manage",
            "action": "tag",
            "paper_id": paper_id,
            "paper_tags": ["survey", "benchmark"],
            "context": ctx.model_dump(),
            "idempotency_key": "idem-tag-2",
        }
    )
    assert tagged.get("tag_result", {}).get("tagged") is True

    listed = app.invoke(
        {
            "workflow": "library_manage",
            "action": "list",
            "context": ctx.model_dump(),
        }
    )
    assert paper_id in listed.get("library_paper_ids", [])
