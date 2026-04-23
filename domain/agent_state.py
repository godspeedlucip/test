from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from domain.evidence import EvidenceSpan
from domain.paper import PaperMetadata


class ExecutionStep(BaseModel):
    step_id: str
    node_name: str
    status: Literal["pending", "running", "succeeded", "failed", "skipped"]
    selected_tool: str | None = None
    tool_input_summary: dict[str, Any] | None = None
    tool_output_summary: dict[str, Any] | None = None
    started_at_ms: int | None = None
    ended_at_ms: int | None = None
    retry_count: int = 0
    error_code: str | None = None


class AgentState(BaseModel):
    user_query: str
    plan: list[str] = Field(default_factory=list)
    execution_steps: list[ExecutionStep] = Field(default_factory=list)
    selected_tool: str | None = None
    tool_input: dict[str, Any] | None = None
    tool_output: dict[str, Any] | None = None
    retrieved_papers: list[PaperMetadata] = Field(default_factory=list)
    working_document_ids: list[str] = Field(default_factory=list)
    evidences: list[EvidenceSpan] = Field(default_factory=list)
    final_answer: str | None = None
    artifacts: list[dict[str, Any]] = Field(default_factory=list)
    judge_results: list[dict[str, Any]] = Field(default_factory=list)
    messages: list[dict[str, str]] = Field(default_factory=list)
    trace_id: str | None = None
