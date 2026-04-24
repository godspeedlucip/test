from __future__ import annotations

from typing import Any

from observability.event_factory import ensure_standard_event_type
from observability.recorder import get_recorder


class ObservabilityEmitter:
    def emit(self, *, event_type: str, trace_id: str, payload: dict[str, Any] | None = None, parent_span_id: str | None = None):
        normalized_type = ensure_standard_event_type(event_type)
        return get_recorder().emit(
            event_type=normalized_type,
            trace_id=trace_id,
            payload=payload or {},
            parent_span_id=parent_span_id,
        )

    def list_trace_events(self, trace_id: str):
        return get_recorder().list_trace_events(trace_id)

    def aggregate_metrics(self, *, start_ms: int | None = None, end_ms: int | None = None):
        return get_recorder().aggregate_metrics(start_ms=start_ms, end_ms=end_ms)


emitter = ObservabilityEmitter()


def get_emitter() -> ObservabilityEmitter:
    return emitter
