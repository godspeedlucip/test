from __future__ import annotations

from typing import Any, Literal

StandardEventType = Literal[
    "request_started",
    "request_finished",
    "step_started",
    "step_finished",
    "tool_called",
    "tool_finished",
    "judge_finished",
    "error_raised",
]

STANDARD_EVENT_TYPES: set[str] = {
    "request_started",
    "request_finished",
    "step_started",
    "step_finished",
    "tool_called",
    "tool_finished",
    "judge_finished",
    "error_raised",
}

LEGACY_EVENT_MAP: dict[str, str] = {
    "workflow_started": "request_started",
    "workflow_finished": "request_finished",
    "node_started": "step_started",
    "node_finished": "step_finished",
    "node_failed": "error_raised",
}


def normalize_event_type(event_type: str) -> str:
    return LEGACY_EVENT_MAP.get(event_type, event_type)


def ensure_standard_event_type(event_type: str) -> str:
    normalized = normalize_event_type(event_type)
    if normalized not in STANDARD_EVENT_TYPES:
        raise ValueError(f"unsupported observability event type: {event_type}")
    return normalized


def make_request_started_payload(*, workflow: str | None = None, entry_step: str | None = None, **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if workflow:
        payload["workflow"] = workflow
    if entry_step:
        payload["entry_step"] = entry_step
    payload.update(extra)
    return payload


def make_request_finished_payload(
    *,
    workflow: str | None = None,
    success: bool,
    total_steps: int,
    errors: list[str] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "success": bool(success),
        "total_steps": int(total_steps),
        "errors": list(errors or []),
    }
    if workflow:
        payload["workflow"] = workflow
    payload.update(extra)
    return payload


def make_step_started_payload(*, step_name: str, attempt: int, max_retries: int, **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "step_name": step_name,
        "attempt": int(attempt),
        "max_retries": int(max_retries),
    }
    payload.update(extra)
    return payload


def make_step_finished_payload(
    *,
    step_name: str,
    attempt: int,
    status: Literal["succeeded", "failed"],
    duration_ms: int,
    error_message: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "step_name": step_name,
        "attempt": int(attempt),
        "status": status,
        "duration_ms": int(duration_ms),
        "error_message": error_message,
    }
    payload.update(extra)
    return payload


def make_error_payload(*, source: str, message: str, **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"source": source, "message": message}
    payload.update(extra)
    return payload
