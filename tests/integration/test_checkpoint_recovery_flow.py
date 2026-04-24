from domain.context import RequestContext
from graph.recovery import apply_human_review_decision, list_checkpoints, load_checkpoint
from graph.workflows.related_work_workflow import build_related_work_workflow
from tools.academic.search_papers import SearchPapersInput, search_papers_tool


def test_human_review_decision_routes_back_to_flow(monkeypatch):
    import graph.nodes.judge_node as judge_node_module

    ctx = RequestContext(user_id="u1", request_id="recover-human-1")
    pids = [x["paper_id"] for x in search_papers_tool.execute(SearchPapersInput(context=ctx, query="agents", top_k=2)).data["papers"][:2]]

    def always_reject(_payload):
        return type(
            "Result",
            (),
            {
                "success": True,
                "data": {
                    "passed": False,
                    "overall_score": 0.1,
                    "dimension_scores": [],
                    "hallucinated_claims": [],
                    "unsupported_claims": ["u1"],
                    "improvement_suggestions": ["needs review"],
                },
                "error": None,
            },
        )()

    monkeypatch.setattr(judge_node_module.judge_answer_quality_tool, "execute", always_reject)

    app = build_related_work_workflow()
    out = app.invoke(
        {
            "workflow": "related_work",
            "user_query": "generate related work",
            "topic": "agents",
            "context": ctx.model_dump(),
            "paper_ids": pids,
            "enable_judge": True,
            "max_revise": 0,
            "human_review_decision": "approved",
        }
    )
    assert out.get("human_review")
    decision_updates = apply_human_review_decision(out, "approved", "looks good")
    assert decision_updates["route_after_human_review"] == "trajectory_judge"


def test_load_checkpoint_returns_state_snapshot():
    ctx = RequestContext(user_id="u1", request_id="recover-checkpoint-1")
    pid = search_papers_tool.execute(SearchPapersInput(context=ctx, query="llm", top_k=1)).data["papers"][0]["paper_id"]
    app = build_related_work_workflow()
    out = app.invoke(
        {
            "workflow": "related_work",
            "user_query": "generate related work",
            "topic": "llm",
            "context": ctx.model_dump(),
            "paper_ids": [pid],
            "enable_judge": False,
        }
    )
    checkpoints = out.get("checkpoints", [])
    assert checkpoints
    listed = list_checkpoints(out.get("trace_id"))
    assert listed
    snapshot = load_checkpoint(checkpoints[-1]["checkpoint_id"])
    assert isinstance(snapshot, dict)
