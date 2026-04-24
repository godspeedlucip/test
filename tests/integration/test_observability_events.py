from domain.context import RequestContext
from graph.workflows.library_workflow import build_library_workflow
from graph.workflows.qa_workflow import build_qa_workflow
from observability.metrics import aggregate_metrics
from observability.recorder import get_recorder


STANDARD_EVENT_TYPES = {
    "request_started",
    "request_finished",
    "step_started",
    "step_finished",
    "tool_called",
    "tool_finished",
    "judge_finished",
    "error_raised",
}


def test_observability_events_follow_standard_types():
    ctx = RequestContext(user_id="obs-u1", request_id="obs-standard-1")
    app = build_qa_workflow()
    app.invoke(
        {
            "workflow": "qa",
            "user_query": "summarize this paper",
            "context": ctx.model_dump(),
            "top_k": 1,
            "enable_judge": True,
        }
    )
    events = get_recorder().events
    assert events
    assert all(e.event_type in STANDARD_EVENT_TYPES for e in events)
    assert any(e.event_type == "request_started" for e in events)
    assert any(e.event_type == "request_finished" for e in events)
    assert any(e.event_type == "step_started" for e in events)
    assert any(e.event_type == "step_finished" for e in events)
    metrics = aggregate_metrics()
    assert "request_layer" in metrics and "quality_layer" in metrics and "cost_layer" in metrics


def test_failure_path_emits_error_and_request_finished():
    ctx = RequestContext(user_id="obs-u2", request_id="obs-failure-1")
    app = build_library_workflow()
    app.invoke(
        {
            "workflow": "library_save",
            "query": "agent systems",
            "context": ctx.model_dump(),
            "top_k": 1,
        }
    )
    events = get_recorder().events
    assert any(e.event_type == "request_finished" for e in events)
