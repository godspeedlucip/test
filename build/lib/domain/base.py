from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ToolError(BaseModel):
    code: str
    message: str
    detail: dict[str, Any] | None = None
    retryable: bool = False
    error_layer: Literal["llm", "tool", "network", "parser", "storage", "judge", "graph"] | None = None


class ToolMeta(BaseModel):
    tool_name: str
    duration_ms: int | None = None
    latency_ms: int | None = None
    cached: bool = False
    trace_id: str | None = None
    span_id: str | None = None
    parent_span_id: str | None = None
    version: str | None = "0.1.0"
    model_name: str | None = None
    prompt_name: str | None = None
    prompt_version: str | None = None
    token_usage: dict[str, int] | None = None
    estimated_cost_usd: float | None = None
    estimated_cost_source: str | None = None
    judge_mode: str | None = None
    fallback_reason: str | None = None


class ToolResult(BaseModel):
    success: bool
    error: ToolError | None = None
    data: dict[str, Any] | None = None
    meta: ToolMeta = Field(default_factory=lambda: ToolMeta(tool_name="unknown"))


class ToolCapability(BaseModel):
    name: str
    category: str
    owner: Literal["python", "java", "platform"]
    has_side_effect: bool = False
    cacheable: bool = False
    observable: bool = True
    judgeable: bool = False
