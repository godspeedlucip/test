from __future__ import annotations

import time
import uuid
from typing import Any, Callable

from observability.recorder import get_recorder


def run_node(node_name: str, state: dict[str, Any], handler: Callable[[dict[str, Any]], dict[str, Any]]) -> dict[str, Any]:
    recorder = get_recorder()
    trace_id = state.get("trace_id") or state.get("context", {}).get("request_id") or str(uuid.uuid4())
    state["trace_id"] = trace_id
    started = recorder.emit(event_type="step_started", trace_id=trace_id, payload={"node": node_name})
    started_ms = int(time.time() * 1000)
    try:
        updates = handler(state)
        elapsed = int(time.time() * 1000) - started_ms
        recorder.emit(
            event_type="step_finished",
            trace_id=trace_id,
            parent_span_id=started.span_id,
            payload={"node": node_name, "duration_ms": elapsed},
        )
        return updates
    except Exception as exc:
        recorder.emit(
            event_type="error_raised",
            trace_id=trace_id,
            parent_span_id=started.span_id,
            payload={"node": node_name, "error": str(exc)},
        )
        return {"errors": state.get("errors", []) + [f"{node_name}: {exc}"]}
