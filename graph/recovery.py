from __future__ import annotations

from typing import Any, Callable

from integrations import get_checkpoint_store


def load_checkpoint(checkpoint_id: str) -> dict[str, Any] | None:
    return get_checkpoint_store().load_checkpoint(checkpoint_id)


def list_checkpoints(trace_id: str) -> list[dict[str, Any]]:
    return [cp.model_dump() for cp in get_checkpoint_store().list_by_trace(trace_id)]


def apply_human_review_decision(state: dict[str, Any], decision: str, note: str | None = None) -> dict[str, Any]:
    normalized = decision.strip().lower()
    if normalized not in {"approved", "rejected"}:
        raise ValueError("decision must be approved or rejected")
    review = dict(state.get("human_review") or {})
    if review:
        review["status"] = normalized
        if note:
            review["decision_note"] = note
    updates = {
        "human_review": review,
        "route_after_human_review": "trajectory_judge" if normalized == "approved" else "revise",
    }
    return updates


def resume_from_checkpoint(checkpoint_id: str, workflow_runner: Callable[[dict[str, Any]], dict[str, Any]]) -> dict[str, Any]:
    state = load_checkpoint(checkpoint_id)
    if state is None:
        raise ValueError(f"checkpoint not found: {checkpoint_id}")
    resumed = dict(state)
    resumed["resumed_from_checkpoint"] = checkpoint_id
    resumed["recovery_mode"] = "checkpoint_resume"
    return workflow_runner(resumed)
