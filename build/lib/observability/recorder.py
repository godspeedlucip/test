from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from domain.observability import ObservabilityEvent
from integrations.trace_store import get_trace_store
from observability.event_factory import ensure_standard_event_type


@dataclass
class InMemoryObservabilityRecorder:
    events: list[ObservabilityEvent] = field(default_factory=list)
    _event_ids: set[tuple[str, str, str]] = field(default_factory=set)

    def record(self, event: ObservabilityEvent) -> None:
        key = (event.trace_id, event.event_type, event.span_id)
        if key in self._event_ids:
            return
        self._event_ids.add(key)
        get_trace_store().append(event)
        self.events.append(event)

    def emit(self, *, event_type: str, trace_id: str, payload: dict | None = None, parent_span_id: str | None = None) -> ObservabilityEvent:
        normalized_type = ensure_standard_event_type(event_type)
        event = ObservabilityEvent(
            event_type=normalized_type,
            trace_id=trace_id,
            span_id=str(uuid.uuid4()),
            parent_span_id=parent_span_id,
            timestamp_ms=int(time.time() * 1000),
            payload=payload or {},
        )
        self.record(event)
        return event

    def list_trace_events(self, trace_id: str) -> list[ObservabilityEvent]:
        return get_trace_store().list_trace_events(trace_id)

    def get_trace(self, trace_id: str):
        return get_trace_store().get_trace(trace_id)

    def aggregate_metrics(self, *, start_ms: int | None = None, end_ms: int | None = None) -> dict:
        return get_trace_store().aggregate_metrics(start_ms=start_ms, end_ms=end_ms)

    def clear(self) -> None:
        self.events.clear()
        self._event_ids.clear()
        get_trace_store().clear()


recorder = InMemoryObservabilityRecorder()


def get_recorder() -> InMemoryObservabilityRecorder:
    return recorder
