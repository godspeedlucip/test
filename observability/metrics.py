from __future__ import annotations

from integrations.trace_store import get_trace_store


def get_trace(trace_id: str):
    return get_trace_store().get_trace(trace_id)


def list_trace_events(trace_id: str):
    return get_trace_store().list_trace_events(trace_id)


def aggregate_metrics(*, trace_id: str | None = None, start_ms: int | None = None, end_ms: int | None = None) -> dict:
    return get_trace_store().aggregate_metrics(trace_id=trace_id, start_ms=start_ms, end_ms=end_ms)


def request_layer(*, start_ms: int | None = None, end_ms: int | None = None) -> dict:
    return aggregate_metrics(start_ms=start_ms, end_ms=end_ms).get("request_layer", {})


def step_layer(*, start_ms: int | None = None, end_ms: int | None = None) -> dict:
    return aggregate_metrics(start_ms=start_ms, end_ms=end_ms).get("step_layer", {})


def quality_layer(*, start_ms: int | None = None, end_ms: int | None = None) -> dict:
    return aggregate_metrics(start_ms=start_ms, end_ms=end_ms).get("quality_layer", {})


def cost_layer(*, start_ms: int | None = None, end_ms: int | None = None) -> dict:
    return aggregate_metrics(start_ms=start_ms, end_ms=end_ms).get("cost_layer", {})
