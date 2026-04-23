from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Callable, Literal
from urllib import error as urlerror
from urllib import request as urlrequest

from pydantic import BaseModel, Field

from integrations.repository import get_repo


class SavePaperToLibraryRequest(BaseModel):
    user_id: str
    paper_id: str
    idempotency_key: str | None = None


class SavePaperToLibraryResponse(BaseModel):
    saved: bool
    paper_ids: list[str] = Field(default_factory=list)


class ListLibraryPapersRequest(BaseModel):
    user_id: str


class ListLibraryPapersResponse(BaseModel):
    paper_ids: list[str] = Field(default_factory=list)


class AddPaperNoteRequest(BaseModel):
    user_id: str
    paper_id: str
    note: str
    idempotency_key: str | None = None


class AddPaperNoteResponse(BaseModel):
    added: bool
    notes_count: int


class RecordFileArtifactRequest(BaseModel):
    task_id: str
    artifact_uri: str
    artifact_type: str = "file"
    metadata: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str | None = None


class RecordFileArtifactResponse(BaseModel):
    recorded: bool
    artifact_id: str


class UpdateTaskStatusRequest(BaseModel):
    task_id: str
    status: str
    message: str | None = None
    idempotency_key: str | None = None


class UpdateTaskStatusResponse(BaseModel):
    updated: bool
    task_id: str
    status: str


class ReportObservabilityEventRequest(BaseModel):
    trace_id: str
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str | None = None


class ReportObservabilityEventResponse(BaseModel):
    accepted: bool
    event_id: str | None = None


class JavaClientError(Exception):
    def __init__(
        self,
        message: str,
        *,
        error_layer: Literal["network", "storage"] = "network",
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.error_layer = error_layer
        self.status_code = status_code


class JavaClientRetryableError(JavaClientError):
    pass


class JavaClientNonRetryableError(JavaClientError):
    pass


class JavaClientConfig(BaseModel):
    base_url: str | None = None
    timeout_seconds: float = 5.0
    auth_header: str | None = None
    max_retries: int = 2
    retry_backoff_seconds: float = 0.1


@dataclass
class TransportResponse:
    status_code: int
    body: dict[str, Any]


TransportFunc = Callable[[str, str, dict[str, str], dict[str, Any], float], TransportResponse]


def _default_transport(
    method: str,
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout_seconds: float,
) -> TransportResponse:
    body = json.dumps(payload).encode("utf-8")
    req = urlrequest.Request(url=url, data=body, headers=headers, method=method)
    try:
        with urlrequest.urlopen(req, timeout=timeout_seconds) as resp:
            raw = resp.read().decode("utf-8")
            parsed = json.loads(raw) if raw.strip() else {}
            return TransportResponse(status_code=int(resp.getcode() or 200), body=parsed)
    except urlerror.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="ignore") if hasattr(exc, "read") else ""
        parsed = {}
        if raw.strip():
            try:
                parsed = json.loads(raw)
            except Exception:
                parsed = {"message": raw}
        status = int(exc.code or 500)
        msg = parsed.get("message", f"HTTP {status}")
        layer: Literal["network", "storage"] = "storage" if status in {409, 423, 507} else "network"
        if status >= 500 or status in {408, 425, 429}:
            raise JavaClientRetryableError(msg, error_layer=layer, status_code=status) from exc
        raise JavaClientNonRetryableError(msg, error_layer=layer, status_code=status) from exc
    except (urlerror.URLError, TimeoutError) as exc:
        raise JavaClientRetryableError(str(exc), error_layer="network") from exc


class JavaClient:
    def __init__(self, config: JavaClientConfig, transport: TransportFunc | None = None) -> None:
        self.config = config
        self._transport = transport or _default_transport
        if not self.config.base_url:
            raise JavaClientNonRetryableError("base_url is required for JavaClient", error_layer="network")

    def _headers(self, idempotency_key: str | None = None) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.config.auth_header:
            headers["Authorization"] = self.config.auth_header
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        return headers

    def _with_retry(self, fn: Callable[[], TransportResponse]) -> TransportResponse:
        attempts = 0
        while True:
            attempts += 1
            try:
                return fn()
            except JavaClientRetryableError:
                if attempts > self.config.max_retries:
                    raise
                time.sleep(self.config.retry_backoff_seconds)

    def _post(
        self,
        *,
        path: str,
        payload: dict[str, Any],
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        url = f"{self.config.base_url.rstrip('/')}/{path.lstrip('/')}"

        def _send() -> TransportResponse:
            return self._transport(
                "POST",
                url,
                self._headers(idempotency_key=idempotency_key),
                payload,
                float(self.config.timeout_seconds),
            )

        response = self._with_retry(_send)
        if response.status_code >= 400:
            layer: Literal["network", "storage"] = "storage" if response.status_code in {409, 423, 507} else "network"
            raise JavaClientNonRetryableError(
                f"HTTP {response.status_code}",
                error_layer=layer,
                status_code=response.status_code,
            )
        return response.body

    def save_paper_to_library(self, req: SavePaperToLibraryRequest) -> SavePaperToLibraryResponse:
        body = self._post(
            path="/library/save-paper",
            payload=req.model_dump(exclude_none=True),
            idempotency_key=req.idempotency_key,
        )
        return SavePaperToLibraryResponse.model_validate(body)

    def list_library_papers(self, req: ListLibraryPapersRequest) -> ListLibraryPapersResponse:
        body = self._post(path="/library/list-papers", payload=req.model_dump(exclude_none=True))
        return ListLibraryPapersResponse.model_validate(body)

    def add_paper_note(self, req: AddPaperNoteRequest) -> AddPaperNoteResponse:
        body = self._post(
            path="/library/add-note",
            payload=req.model_dump(exclude_none=True),
            idempotency_key=req.idempotency_key,
        )
        return AddPaperNoteResponse.model_validate(body)

    def record_file_artifact(self, req: RecordFileArtifactRequest) -> RecordFileArtifactResponse:
        body = self._post(
            path="/artifacts/record",
            payload=req.model_dump(exclude_none=True),
            idempotency_key=req.idempotency_key,
        )
        return RecordFileArtifactResponse.model_validate(body)

    def update_task_status(self, req: UpdateTaskStatusRequest) -> UpdateTaskStatusResponse:
        body = self._post(
            path="/tasks/update-status",
            payload=req.model_dump(exclude_none=True),
            idempotency_key=req.idempotency_key,
        )
        return UpdateTaskStatusResponse.model_validate(body)

    def report_observability_event(self, req: ReportObservabilityEventRequest) -> ReportObservabilityEventResponse:
        body = self._post(
            path="/observability/report-event",
            payload=req.model_dump(exclude_none=True),
            idempotency_key=req.idempotency_key,
        )
        return ReportObservabilityEventResponse.model_validate(body)


class MockJavaClient:
    def __init__(self) -> None:
        self.task_status: dict[str, str] = {}
        self.artifacts: dict[str, dict[str, Any]] = {}
        self.observability_events: list[dict[str, Any]] = []

    def save_paper_to_library(self, req: SavePaperToLibraryRequest) -> SavePaperToLibraryResponse:
        repo = get_repo()
        repo.library.setdefault(req.user_id, [])
        if req.paper_id not in repo.library[req.user_id]:
            repo.library[req.user_id].append(req.paper_id)
        return SavePaperToLibraryResponse(saved=True, paper_ids=list(repo.library[req.user_id]))

    def list_library_papers(self, req: ListLibraryPapersRequest) -> ListLibraryPapersResponse:
        repo = get_repo()
        return ListLibraryPapersResponse(paper_ids=list(repo.library.get(req.user_id, [])))

    def add_paper_note(self, req: AddPaperNoteRequest) -> AddPaperNoteResponse:
        repo = get_repo()
        repo.notes.setdefault(req.paper_id, []).append(req.note)
        return AddPaperNoteResponse(added=True, notes_count=len(repo.notes[req.paper_id]))

    def record_file_artifact(self, req: RecordFileArtifactRequest) -> RecordFileArtifactResponse:
        artifact_id = f"artifact-{len(self.artifacts) + 1}"
        self.artifacts[artifact_id] = req.model_dump()
        return RecordFileArtifactResponse(recorded=True, artifact_id=artifact_id)

    def update_task_status(self, req: UpdateTaskStatusRequest) -> UpdateTaskStatusResponse:
        self.task_status[req.task_id] = req.status
        return UpdateTaskStatusResponse(updated=True, task_id=req.task_id, status=req.status)

    def report_observability_event(self, req: ReportObservabilityEventRequest) -> ReportObservabilityEventResponse:
        event_id = f"evt-{len(self.observability_events) + 1}"
        self.observability_events.append({"event_id": event_id, **req.model_dump()})
        return ReportObservabilityEventResponse(accepted=True, event_id=event_id)


java_client: JavaClient | MockJavaClient | None = None


def build_java_client() -> JavaClient | MockJavaClient:
    base_url = os.getenv("JAVA_CLIENT_BASE_URL")
    if not base_url:
        return MockJavaClient()
    config = JavaClientConfig(
        base_url=base_url,
        timeout_seconds=float(os.getenv("JAVA_CLIENT_TIMEOUT_SECONDS", "5")),
        auth_header=os.getenv("JAVA_CLIENT_AUTH_HEADER"),
        max_retries=int(os.getenv("JAVA_CLIENT_MAX_RETRIES", "2")),
        retry_backoff_seconds=float(os.getenv("JAVA_CLIENT_RETRY_BACKOFF_SECONDS", "0.1")),
    )
    return JavaClient(config=config)


def get_java_client() -> JavaClient | MockJavaClient:
    global java_client
    if java_client is None:
        java_client = build_java_client()
    return java_client
