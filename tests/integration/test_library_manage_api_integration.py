from fastapi.testclient import TestClient

from app.main import app


def test_library_manage_api_actions():
    client = TestClient(app)

    save_resp = client.post(
        "/workflows/library/manage",
        json={
            "action": "save",
            "query": "retrieval augmented generation",
            "context": {"user_id": "api-int-lib", "request_id": "api-int-lib-save"},
            "idempotency_key": "api-int-lib-save-idem",
            "top_k": 3,
        },
    )
    assert save_resp.status_code == 200
    saved_paper_id = save_resp.json().get("saved_paper_id")
    assert saved_paper_id

    note_resp = client.post(
        "/workflows/library/manage",
        json={
            "action": "add_note",
            "paper_id": saved_paper_id,
            "library_note": "important paper",
            "context": {"user_id": "api-int-lib", "request_id": "api-int-lib-note"},
            "idempotency_key": "api-int-lib-note-idem",
        },
    )
    assert note_resp.status_code == 200
    assert note_resp.json().get("note_result", {}).get("added") is True

    tag_resp = client.post(
        "/workflows/library/manage",
        json={
            "action": "tag",
            "paper_id": saved_paper_id,
            "paper_tags": ["rag", "survey"],
            "context": {"user_id": "api-int-lib", "request_id": "api-int-lib-tag"},
            "idempotency_key": "api-int-lib-tag-idem",
        },
    )
    assert tag_resp.status_code == 200
    assert tag_resp.json().get("tag_result", {}).get("tagged") is True

    list_resp = client.post(
        "/workflows/library/manage",
        json={
            "action": "list",
            "context": {"user_id": "api-int-lib", "request_id": "api-int-lib-list"},
        },
    )
    assert list_resp.status_code == 200
    assert saved_paper_id in list_resp.json().get("library_paper_ids", [])
