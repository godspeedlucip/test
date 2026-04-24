from observability.metrics import aggregate_metrics, get_trace, list_trace_events
from observability.recorder import get_recorder


def test_trace_store_query_and_metrics():
    recorder = get_recorder()
    recorder.emit(event_type="request_started", trace_id="t1", payload={"workflow": "qa"})
    recorder.emit(event_type="step_started", trace_id="t1", payload={"step_name": "intent_router", "attempt": 1, "max_retries": 1})
    recorder.emit(event_type="step_finished", trace_id="t1", payload={"step_name": "intent_router", "attempt": 1, "status": "succeeded", "duration_ms": 12})
    recorder.emit(event_type="tool_called", trace_id="t1", payload={"tool_name": "ask_paper"})
    recorder.emit(
        event_type="tool_finished",
        trace_id="t1",
        payload={"tool_name": "ask_paper", "token_usage": {"prompt_tokens": 50, "completion_tokens": 10, "total_tokens": 60}},
    )
    recorder.emit(event_type="judge_finished", trace_id="t1", payload={"overall_score": 0.9, "passed": True})
    recorder.emit(event_type="request_finished", trace_id="t1", payload={"success": True, "total_steps": 1, "errors": []})

    trace = get_trace("t1")
    assert trace is not None
    assert trace.trace_id == "t1"

    events = list_trace_events("t1")
    assert len(events) == 7

    metrics = aggregate_metrics()
    assert metrics["request_count"] == 1
    assert metrics["tool_call_count"] == 1
    assert metrics["success_rate"] == 1.0
    assert metrics["request_layer"]["request_count"] == 1
    assert metrics["step_layer"]["step_count"] == 1
    assert metrics["quality_layer"]["judge_events"] == 1
    assert metrics["cost_layer"]["token_usage"]["total_tokens"] == 60
    assert metrics["total_tokens"] == 60
    assert metrics["tool_call_count"] == 1
    assert metrics["error_count"] == 0

    per_trace = aggregate_metrics(trace_id="t1")
    assert per_trace["trace_id"] == "t1"
    assert per_trace["judge_score"] == 0.9
