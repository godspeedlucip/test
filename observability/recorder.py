from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from domain.observability import ObservabilityEvent
from observability.event_factory import ensure_standard_event_type


@dataclass
class InMemoryObservabilityRecorder:
    events: list[ObservabilityEvent] = field(default_factory=list)

    def record(self, event: ObservabilityEvent) -> None:
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


recorder = InMemoryObservabilityRecorder()


def get_recorder() -> InMemoryObservabilityRecorder:
    return recorder
