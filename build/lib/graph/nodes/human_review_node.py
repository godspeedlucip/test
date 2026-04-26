import uuid

from graph.nodes.common import run_node
from graph.recovery import apply_human_review_decision


def human_review_node(state: dict):
    def _impl(s: dict):
        incoming_decision = s.get("human_review_decision")
        if incoming_decision and s.get("human_review"):
            updates = apply_human_review_decision(s, incoming_decision, s.get("human_review_note"))
            return {
                **updates,
                "artifacts": s.get("artifacts", []) + [{"type": "human_review_decision", "payload": updates}],
            }

        latest = (s.get("judge_results") or [{}])[-1]
        suggestions = latest.get("improvement_suggestions", [])
        reason = "; ".join(suggestions) if suggestions else "Judge rejected after max revisions"
        workflow = s.get("workflow")
        trace_id = s.get("trace_id") or "unknown-trace"
        task = {
            "review_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{trace_id}:{workflow}:human_review")),
            "trace_id": trace_id,
            "reason": reason,
            "status": "pending",
            "suggested_action": "human_review_required",
        }
        next_route = "trajectory_judge" if workflow == "related_work" else "proceed"
        return {
            "human_review": task,
            "route_after_human_review": next_route,
            "artifacts": s.get("artifacts", []) + [{"type": "human_review", "payload": task}],
        }

    return run_node("human_review_node", state, _impl)
