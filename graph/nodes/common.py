from __future__ import annotations

import time
import uuid
from typing import Any, Callable

from integrations import get_checkpoint_store
from observability.emitter import get_emitter
from observability.event_factory import (
    make_error_payload,
    make_request_finished_payload,
    make_request_started_payload,
    make_step_finished_payload,
    make_step_started_payload,
)


def _resolve_max_retries(state: dict[str, Any]) -> int:
    runtime = state.get("runtime", {})
    raw = state.get("max_retries", runtime.get("max_retries", 2))
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = 2
    return max(0, min(2, value))


def _summarize_payload(payload: Any, *, max_keys: int = 12, max_list: int = 8) -> Any:
    if isinstance(payload, dict):
        summary: dict[str, Any] = {}
        for idx, (k, v) in enumerate(payload.items()):
            if idx >= max_keys:
                summary["..."] = f"+{len(payload) - max_keys} keys"
                break
            summary[k] = _summarize_payload(v, max_keys=max_keys, max_list=max_list)
        return summary
    if isinstance(payload, list):
        if len(payload) > max_list:
            return [_summarize_payload(x, max_keys=max_keys, max_list=max_list) for x in payload[:max_list]] + [
                f"... +{len(payload) - max_list} items"
            ]
        return [_summarize_payload(x, max_keys=max_keys, max_list=max_list) for x in payload]
    if isinstance(payload, str):
        return payload if len(payload) <= 240 else payload[:240] + "..."
    if isinstance(payload, (int, float, bool)) or payload is None:
        return payload
    return str(payload)


def run_node(node_name: str, state: dict[str, Any], handler: Callable[[dict[str, Any]], dict[str, Any]]) -> dict[str, Any]:
    emitter = get_emitter()
    checkpoint_store = get_checkpoint_store()
    trace_id = state.get("trace_id") or state.get("context", {}).get("request_id") or str(uuid.uuid4())
    state["trace_id"] = trace_id

    max_retries = _resolve_max_retries(state)
    execution_steps = list(state.get("execution_steps", []))
    checkpoints = list(state.get("checkpoints", []))
    base_errors = list(state.get("errors", []))
    request_started = bool(state.get("request_started", False))
    request_finished = bool(state.get("request_finished", False))

    if not request_started:
        emitter.emit(
            event_type="request_started",
            trace_id=trace_id,
            payload=make_request_started_payload(
                workflow=state.get("workflow"),
                entry_step=node_name,
                max_retries=max_retries,
            ),
        )
        request_started = True

    for attempt in range(max_retries + 1):
        step_started_event = emitter.emit(
            event_type="step_started",
            trace_id=trace_id,
            payload=make_step_started_payload(step_name=node_name, attempt=attempt + 1, max_retries=max_retries),
        )
        started_ms = int(time.time() * 1000)

        input_summary = _summarize_payload(
            {
                "trace_id": trace_id,
                "attempt": attempt + 1,
                "state": state,
            }
        )

        before_cp = checkpoint_store.save(trace_id=trace_id, node_name=f"{node_name}:before", state=state)
        checkpoints.append(before_cp.model_dump())

        try:
            updates = handler(state) or {}
            ended_ms = int(time.time() * 1000)

            output_summary = _summarize_payload(updates)
            after_state = dict(state)
            after_state.update(updates)
            after_cp = checkpoint_store.save(trace_id=trace_id, node_name=f"{node_name}:after", state=after_state)
            checkpoints.append(after_cp.model_dump())

            emitter.emit(
                event_type="step_finished",
                trace_id=trace_id,
                parent_span_id=step_started_event.span_id,
                payload=make_step_finished_payload(
                    step_name=node_name,
                    attempt=attempt + 1,
                    status="succeeded",
                    duration_ms=ended_ms - started_ms,
                ),
            )
            execution_steps.append(
                {
                    "step_id": str(uuid.uuid4()),
                    "node_name": node_name,
                    "status": "succeeded",
                    "started_at": started_ms,
                    "finished_at": ended_ms,
                    "retry_count": attempt,
                    "input_summary": input_summary,
                    "output_summary": output_summary,
                    "error_message": None,
                }
            )
            result = {
                "trace_id": trace_id,
                "request_started": request_started,
                "request_finished": request_finished,
                "execution_steps": execution_steps,
                "checkpoints": checkpoints,
            }
            result.update(updates)

            if node_name == "observability_node" and not request_finished:
                finished_errors = list(result.get("errors", []))
                emitter.emit(
                    event_type="request_finished",
                    trace_id=trace_id,
                    payload=make_request_finished_payload(
                        workflow=state.get("workflow"),
                        success=not finished_errors,
                        total_steps=len(execution_steps),
                        errors=finished_errors,
                    ),
                )
                result["request_finished"] = True
            return result
        except Exception as exc:
            ended_ms = int(time.time() * 1000)
            error_message = str(exc)

            emitter.emit(
                event_type="error_raised",
                trace_id=trace_id,
                parent_span_id=step_started_event.span_id,
                payload=make_error_payload(
                    source=node_name,
                    message=error_message,
                    attempt=attempt + 1,
                ),
            )
            emitter.emit(
                event_type="step_finished",
                trace_id=trace_id,
                parent_span_id=step_started_event.span_id,
                payload=make_step_finished_payload(
                    step_name=node_name,
                    attempt=attempt + 1,
                    status="failed",
                    duration_ms=ended_ms - started_ms,
                    error_message=error_message,
                ),
            )
            execution_steps.append(
                {
                    "step_id": str(uuid.uuid4()),
                    "node_name": node_name,
                    "status": "failed",
                    "started_at": started_ms,
                    "finished_at": ended_ms,
                    "retry_count": attempt,
                    "input_summary": input_summary,
                    "output_summary": None,
                    "error_message": error_message,
                }
            )

            failed_cp = checkpoint_store.save(
                trace_id=trace_id,
                node_name=f"{node_name}:failed",
                state={
                    **state,
                    "last_error": error_message,
                    "failed_node": node_name,
                    "attempt": attempt + 1,
                },
            )
            checkpoints.append(failed_cp.model_dump())
            if attempt < max_retries:
                continue

            final_errors = base_errors + [f"{node_name}: {error_message}"]
            if not request_finished:
                emitter.emit(
                    event_type="request_finished",
                    trace_id=trace_id,
                    payload=make_request_finished_payload(
                        workflow=state.get("workflow"),
                        success=False,
                        total_steps=len(execution_steps),
                        errors=final_errors,
                    ),
                )
                request_finished = True
            return {
                "trace_id": trace_id,
                "request_started": request_started,
                "request_finished": request_finished,
                "execution_steps": execution_steps,
                "checkpoints": checkpoints,
                "errors": final_errors,
            }

    return {
        "trace_id": trace_id,
        "request_started": request_started,
        "request_finished": request_finished,
        "execution_steps": execution_steps,
        "checkpoints": checkpoints,
        "errors": base_errors,
    }
