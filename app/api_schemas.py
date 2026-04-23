from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from domain.context import RequestContext


class WorkflowBaseResponse(BaseModel):
    trace_id: str | None = None
    final_answer: str | None = None
    errors: list[str] = Field(default_factory=list)
    execution_steps: list[dict[str, Any]] = Field(default_factory=list)


class QaWorkflowRequest(BaseModel):
    user_query: str
    context: RequestContext
    paper_ids: list[str] = Field(default_factory=list)
    enable_judge: bool = True


class CompareWorkflowRequest(BaseModel):
    user_query: str
    context: RequestContext
    paper_ids: list[str] = Field(default_factory=list)
    enable_judge: bool = True


class RelatedWorkWorkflowRequest(BaseModel):
    user_query: str
    topic: str
    context: RequestContext
    paper_ids: list[str] = Field(default_factory=list)
    enable_judge: bool = True
    max_revise: int = 1


class LibrarySaveWorkflowRequest(BaseModel):
    query: str
    context: RequestContext
    paper_id: str | None = None
    top_k: int = 5


class LibrarySaveWorkflowResponse(WorkflowBaseResponse):
    selected_paper_id: str | None = None
    saved_paper_id: str | None = None
    save_result: dict[str, Any] | None = None
