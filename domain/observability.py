from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ObservabilityEvent(BaseModel):
    event_type: Literal[
        "request_started",
        "request_finished",
        "step_started",
        "step_finished",
        "tool_called",
        "tool_finished",
        "judge_finished",
        "error_raised",
    ]
    trace_id: str
    span_id: str
    parent_span_id: str | None = None
    timestamp_ms: int
    payload: dict[str, Any] = Field(default_factory=dict)


class ExecutionTrace(BaseModel):
    trace_id: str
    request_id: str
    user_query: str
    started_at_ms: int
    ended_at_ms: int | None = None
    final_status: Literal["succeeded", "failed", "partial"] | None = None
    total_steps: int = 0
    total_tool_calls: int = 0


class CheckpointState(BaseModel):
    checkpoint_id: str
    trace_id: str
    node_name: str
    serialized_state_uri: str
    created_at_ms: int


class HumanReviewTask(BaseModel):
    review_id: str
    trace_id: str
    reason: str
    status: Literal["pending", "approved", "rejected"] = "pending"
    suggested_action: str | None = None
