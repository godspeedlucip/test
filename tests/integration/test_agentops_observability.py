from domain.context import RequestContext
from graph.workflows.qa_workflow import build_qa_workflow
from graph.workflows.related_work_workflow import build_related_work_workflow
from observability.recorder import get_recorder


def test_execution_steps_written_with_required_fields():
    ctx = RequestContext(user_id="u1", request_id="agentops-steps")
    app = build_qa_workflow()
    out = app.invoke(
        {
            "user_query": "what is the contribution of agent observability methods?",
            "context": ctx.model_dump(),
            "top_k": 1,
            "enable_judge": True,
        }
    )

    steps = out.get("execution_steps", [])
    assert steps
    required = {
        "step_id",
        "node_name",
        "status",
        "started_at",
        "finished_at",
        "retry_count",
        "input_summary",
        "output_summary",
        "error_message",
    }
    for step in steps:
        assert required.issubset(step.keys())
    assert any(e.event_type == "request_started" for e in get_recorder().events)
    assert any(e.event_type == "request_finished" for e in get_recorder().events)


def test_node_failure_then_retry_success(monkeypatch):
    import graph.nodes.related_work_node as related_node_module

    ctx = RequestContext(user_id="u1", request_id="agentops-retry-success")
    original_execute = related_node_module.generate_related_work_tool.execute
    calls = {"n": 0}

    def flaky(payload):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("transient generation error")
        return original_execute(payload)

    monkeypatch.setattr(related_node_module.generate_related_work_tool, "execute", flaky)

    app = build_related_work_workflow()
    out = app.invoke(
        {
            "workflow": "related_work",
            "user_query": "generate related work",
            "topic": "observability in agents",
            "context": ctx.model_dump(),
            "top_k": 2,
            "enable_judge": False,
            "max_retries": 2,
        }
    )

    target_steps = [s for s in out.get("execution_steps", []) if s.get("node_name") == "related_work_node"]
    assert any(s.get("status") == "failed" for s in target_steps)
    assert any(s.get("status") == "succeeded" for s in target_steps)
    assert any(e.event_type == "error_raised" for e in get_recorder().events)


def test_retry_exhausted_enters_failure_state(monkeypatch):
    import graph.nodes.ask_node as ask_node_module

    ctx = RequestContext(user_id="u1", request_id="agentops-retry-fail")

    def always_fail(_payload):
        raise RuntimeError("persistent ask failure")

    monkeypatch.setattr(ask_node_module.ask_paper_tool, "execute", always_fail)

    app = build_qa_workflow()
    out = app.invoke(
        {
            "user_query": "what is this paper about?",
            "context": ctx.model_dump(),
            "top_k": 1,
            "enable_judge": False,
            "max_retries": 1,
        }
    )

    failed_steps = [s for s in out.get("execution_steps", []) if s.get("node_name") == "ask_node" and s.get("status") == "failed"]
    assert len(failed_steps) >= 2
    assert out.get("errors")


def test_judge_finished_event_emitted():
    ctx = RequestContext(user_id="u1", request_id="agentops-judge-event")
    app = build_qa_workflow()
    app.invoke(
        {
            "user_query": "summarize method",
            "context": ctx.model_dump(),
            "top_k": 1,
            "enable_judge": True,
        }
    )
    assert any(e.event_type == "judge_finished" for e in get_recorder().events)
