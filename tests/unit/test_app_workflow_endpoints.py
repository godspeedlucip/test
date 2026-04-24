from fastapi.testclient import TestClient

from app.main import app
from tools.academic.search_papers import SearchPapersInput, search_papers_tool
from domain.context import RequestContext


def _paper_ids(top_k: int = 2) -> list[str]:
    ctx = RequestContext(user_id="api-u1", request_id="api-seed")
    out = search_papers_tool.execute(SearchPapersInput(context=ctx, query="workflow api", top_k=top_k))
    return [p["paper_id"] for p in out.data["papers"][:top_k]]


def test_post_workflows_qa():
    client = TestClient(app)
    pids = _paper_ids(1)
    response = client.post(
        "/workflows/qa",
        json={
            "user_query": "what is this about?",
            "context": {"user_id": "api-u1", "request_id": "api-qa-1"},
            "paper_ids": pids,
            "enable_judge": True,
        },
    )
    assert response.status_code == 200
    assert "execution_steps" in response.json()


def test_post_workflows_compare_related_and_library():
    client = TestClient(app)
    pids = _paper_ids(2)

    cmp_resp = client.post(
        "/workflows/compare",
        json={
            "user_query": "compare these papers",
            "context": {"user_id": "api-u2", "request_id": "api-cmp-1"},
            "paper_ids": pids,
            "enable_judge": True,
        },
    )
    assert cmp_resp.status_code == 200

    rw_resp = client.post(
        "/workflows/related-work",
        json={
            "user_query": "generate related work",
            "topic": "agent observability",
            "context": {"user_id": "api-u3", "request_id": "api-rw-1"},
            "paper_ids": pids,
            "enable_judge": True,
            "max_revise": 1,
        },
    )
    assert rw_resp.status_code == 200

    lib_resp = client.post(
        "/workflows/library/save",
        json={
            "query": "retrieval augmented generation",
            "context": {"user_id": "api-u4", "request_id": "api-lib-1"},
            "top_k": 3,
        },
    )
    assert lib_resp.status_code == 200
    assert lib_resp.json().get("save_result", {}).get("saved") is True

    manage_save = client.post(
        "/workflows/library/manage",
        json={
            "action": "save",
            "query": "retrieval augmented generation",
            "context": {"user_id": "api-u4", "request_id": "api-lib-manage-1"},
            "idempotency_key": "api-lib-manage-save-1",
            "top_k": 3,
        },
    )
    assert manage_save.status_code == 200
    saved_id = manage_save.json().get("saved_paper_id")
    assert saved_id

    manage_note = client.post(
        "/workflows/library/manage",
        json={
            "action": "add_note",
            "paper_id": saved_id,
            "library_note": "important baseline",
            "context": {"user_id": "api-u4", "request_id": "api-lib-manage-note-1"},
            "idempotency_key": "api-lib-manage-note-1",
        },
    )
    assert manage_note.status_code == 200
    assert manage_note.json().get("note_result", {}).get("added") is True
