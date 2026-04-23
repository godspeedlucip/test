from __future__ import annotations

from domain.observability import ObservabilityEvent
from observability.recorder import get_recorder


class InMemoryTraceStore:
    def append(self, event: ObservabilityEvent) -> None:
        get_recorder().record(event)


trace_store = InMemoryTraceStore()


def get_trace_store() -> InMemoryTraceStore:
    return trace_store
