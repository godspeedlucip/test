from graph.nodes.common import run_node


_COMPUTE_KEYWORDS = {
    "run code",
    "execute code",
    "python",
    "notebook",
    "analyze table",
    "statistics",
    "plot",
    "chart",
    "visualize",
    "csv",
    "tsv",
    "xlsx",
}


def _should_compute(state: dict) -> bool:
    if state.get("analysis_code") or state.get("table_uri"):
        return True
    query = (state.get("user_query") or "").lower()
    return any(k in query for k in _COMPUTE_KEYWORDS)


def intent_router(state: dict):
    def _impl(s: dict):
        query = s.get("user_query", "")
        compute_requested = _should_compute(s)
        if compute_requested:
            plan = ["compute_node", "compose_node"]
            route = "compute"
        elif s.get("workflow") == "related_work" or s.get("topic"):
            plan = [
                "search_node",
                "resolve_identity_node",
                "prepare_documents",
                "related_work_node",
                "judge_node",
                "trajectory_judge_node",
                "compose_node",
            ]
            route = "documents"
        elif s.get("paper_ids") and len(s.get("paper_ids", [])) > 1:
            plan = ["search_node", "prepare_documents", "compare_node", "export_node", "compose_node"]
            route = "documents"
        else:
            plan = ["search_node", "resolve_identity_node", "prepare_documents", "ask_node", "compose_node"]
            route = "documents"
        return {
            "plan": plan,
            "intent_route": route,
            "compute_requested": compute_requested,
            "question": s.get("question", query),
            "max_revise": int(s.get("max_revise", 1)),
            "revise_count": int(s.get("revise_count", 0)),
        }

    return run_node("intent_router", state, _impl)
