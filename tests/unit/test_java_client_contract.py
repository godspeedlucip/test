from __future__ import annotations

import pytest

from integrations.java_client import (
    AddPaperNoteRequest,
    JavaClient,
    JavaClientConfig,
    JavaClientNonRetryableError,
    JavaClientRetryableError,
    ListLibraryPapersRequest,
    MockJavaClient,
    SavePaperToLibraryRequest,
    TransportResponse,
)


def test_mock_java_client_library_contract():
    client = MockJavaClient()

    save = client.save_paper_to_library(SavePaperToLibraryRequest(user_id="u1", paper_id="p1"))
    assert save.saved
    assert save.paper_ids == ["p1"]

    note = client.add_paper_note(AddPaperNoteRequest(user_id="u1", paper_id="p1", note="important"))
    assert note.added
    assert note.notes_count == 1

    listed = client.list_library_papers(ListLibraryPapersRequest(user_id="u1"))
    assert listed.paper_ids == ["p1"]


def test_java_client_retries_only_retryable_errors():
    calls: list[dict] = []

    def transport(method: str, url: str, headers: dict[str, str], payload: dict, timeout: float) -> TransportResponse:
        calls.append({"method": method, "url": url, "headers": dict(headers), "payload": dict(payload), "timeout": timeout})
        if len(calls) == 1:
            raise JavaClientRetryableError("temporary network issue", error_layer="network", status_code=503)
        return TransportResponse(status_code=200, body={"saved": True, "paper_ids": ["p9"]})

    client = JavaClient(
        config=JavaClientConfig(
            base_url="http://java-platform.local",
            timeout_seconds=3,
            auth_header="Bearer token-1",
            max_retries=2,
            retry_backoff_seconds=0,
        ),
        transport=transport,
    )
    response = client.save_paper_to_library(
        SavePaperToLibraryRequest(user_id="u1", paper_id="p9", idempotency_key="idem-1")
    )
    assert response.saved
    assert len(calls) == 2
    assert calls[0]["headers"]["Authorization"] == "Bearer token-1"
    assert calls[0]["headers"]["Idempotency-Key"] == "idem-1"


def test_java_client_non_retryable_errors_not_retried():
    calls = 0

    def transport(method: str, url: str, headers: dict[str, str], payload: dict, timeout: float) -> TransportResponse:
        nonlocal calls
        calls += 1
        raise JavaClientNonRetryableError("bad request", error_layer="storage", status_code=400)

    client = JavaClient(
        config=JavaClientConfig(base_url="http://java-platform.local", max_retries=3, retry_backoff_seconds=0),
        transport=transport,
    )
    with pytest.raises(JavaClientNonRetryableError):
        client.list_library_papers(ListLibraryPapersRequest(user_id="u1"))
    assert calls == 1
