from domain.base import ToolMeta, ToolResult
from domain.context import RequestContext
from graph.workflows.related_work_workflow import build_related_work_workflow
from observability.recorder import get_recorder


def test_related_work_workflow_success_path():
    ctx = RequestContext(user_id="u1", request_id="wf-related-success")

    app = build_related_work_workflow()
    out = app.invoke(
        {
            "workflow": "related_work",
            "user_query": "Generate related work for transformer methods",
            "topic": "transformer methods",
            "context": ctx.model_dump(),
            "top_k": 2,
            "enable_judge": True,
            "max_revise": 1,
        }
    )

    assert out.get("related_work")
    assert out.get("final_answer")
    assert out.get("trajectory_judge_result")
    assert any((x or {}).get("judge_stage") == "trajectory" for x in out.get("judge_results", []))
    assert not out.get("human_review")
    assert any(s.get("node_name") == "related_work_node" and s.get("status") == "succeeded" for s in out.get("execution_steps", []))
    assert any(e.event_type == "request_finished" for e in get_recorder().events)


def test_related_work_judge_reject_then_revise_success(monkeypatch):
    import graph.nodes.judge_node as judge_node_module

    ctx = RequestContext(user_id="u1", request_id="wf-related-revise")
    calls = {"n": 0}

    def fake_execute(_payload):
        calls["n"] += 1
        passed = calls["n"] >= 2
        return ToolResult(
            success=True,
            data={
                "passed": passed,
                "overall_score": 0.8 if passed else 0.3,
                "dimension_scores": [],
                "hallucinated_claims": [] if passed else ["claim_without_evidence"],
                "unsupported_claims": [] if passed else ["unsupported_statement"],
                "improvement_suggestions": [] if passed else ["Add explicit evidence alignment"],
            },
            meta=ToolMeta(tool_name="judge_answer_quality"),
        )

    monkeypatch.setattr(judge_node_module.judge_answer_quality_tool, "execute", fake_execute)

    app = build_related_work_workflow()
    out = app.invoke(
        {
            "workflow": "related_work",
            "user_query": "Generate related work",
            "topic": "retrieval augmentation",
            "context": ctx.model_dump(),
            "top_k": 2,
            "enable_judge": True,
            "max_revise": 2,
        }
    )

    assert out.get("final_answer")
    assert out.get("revise_count") == 1
    assert not out.get("human_review")
    assert any((x or {}).get("judge_stage") == "trajectory" for x in out.get("judge_results", []))
    assert any(a.get("type") == "revision" for a in out.get("artifacts", []))


def test_related_work_judge_reject_to_human_review(monkeypatch):
    import graph.nodes.judge_node as judge_node_module

    ctx = RequestContext(user_id="u1", request_id="wf-related-human-review")

    def always_reject(_payload):
        return ToolResult(
            success=True,
            data={
                "passed": False,
                "overall_score": 0.2,
                "dimension_scores": [],
                "hallucinated_claims": ["h1"],
                "unsupported_claims": ["u1"],
                "improvement_suggestions": ["Strengthen evidence coverage"],
            },
            meta=ToolMeta(tool_name="judge_answer_quality"),
        )

    monkeypatch.setattr(judge_node_module.judge_answer_quality_tool, "execute", always_reject)

    app = build_related_work_workflow()
    out = app.invoke(
        {
            "workflow": "related_work",
            "user_query": "Generate related work",
            "topic": "efficient transformers",
            "context": ctx.model_dump(),
            "top_k": 2,
            "enable_judge": True,
            "max_revise": 1,
        }
    )

    assert out.get("human_review")
    assert out["human_review"]["status"] == "pending"
    assert out.get("revise_count") == 1
    assert any(a.get("type") == "human_review" for a in out.get("artifacts", []))


def test_related_work_node_failure_then_retry_success(monkeypatch):
    import graph.nodes.related_work_node as related_node_module

    ctx = RequestContext(user_id="u1", request_id="wf-related-retry")
    original_execute = related_node_module.generate_related_work_tool.execute
    calls = {"n": 0}

    def flaky_execute(payload):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("temporary generation failure")
        return original_execute(payload)

    monkeypatch.setattr(related_node_module.generate_related_work_tool, "execute", flaky_execute)

    app = build_related_work_workflow()
    out = app.invoke(
        {
            "workflow": "related_work",
            "user_query": "Generate related work with retries",
            "topic": "graph transformers",
            "context": ctx.model_dump(),
            "top_k": 2,
            "enable_judge": False,
            "max_retries": 2,
        }
    )

    statuses = [s.get("status") for s in out.get("execution_steps", []) if s.get("node_name") == "related_work_node"]
    assert "failed" in statuses
    assert "succeeded" in statuses
    assert out.get("final_answer")
    assert any(e.event_type == "error_raised" for e in get_recorder().events)
