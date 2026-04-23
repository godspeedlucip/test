from graph.nodes.common import run_node


def intent_router(state: dict):
    def _impl(s: dict):
        query = s.get("user_query", "")
        plan = ["prepare_documents"]
        if s.get("paper_ids") and len(s.get("paper_ids", [])) > 1:
            plan.extend(["compare_node", "export_node"])
        else:
            plan.append("ask_node")
        return {"plan": plan, "question": s.get("question", query)}

    return run_node("intent_router", state, _impl)
