from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from domain.evidence import EvidenceSpan
from domain.paper import PaperMetadata


class AgentState(BaseModel):
    workflow: str = "qa"
    context: dict[str, Any] = Field(default_factory=dict)
    user_query: str = ""
    question: str | None = None
    query: str | None = None
    action: str | None = None
    idempotency_key: str | None = None
    max_retries: int = 2
    top_k: int = 10
    authors: list[str] = Field(default_factory=list)
    year_from: int | None = None
    year_to: int | None = None
    venue: str | None = None
    sources: list[str] = Field(default_factory=lambda: ["openalex", "crossref", "arxiv"])
    paper_queries: list[str] = Field(default_factory=list)
    paper_id: str | None = None
    topic: str | None = None
    plan: list[str] = Field(default_factory=list)
    execution_steps: list[dict[str, Any]] = Field(default_factory=list)
    selected_tool: str | None = None
    tool_input: dict[str, Any] | None = None
    tool_output: dict[str, Any] | None = None
    retrieved_papers: list[PaperMetadata] = Field(default_factory=list)
    working_document_ids: list[str] = Field(default_factory=list)
    paper_ids: list[str] = Field(default_factory=list)
    document_ids: list[str] = Field(default_factory=list)
    paper_details: dict[str, dict[str, Any]] = Field(default_factory=dict)
    library_candidates: list[dict[str, Any]] = Field(default_factory=list)
    library_search_result: dict[str, Any] = Field(default_factory=dict)
    selected_paper_id: str | None = None
    saved_paper_id: str | None = None
    save_result: dict[str, Any] = Field(default_factory=dict)
    library_paper_ids: list[str] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)
    library_note: str | None = None
    note_result: dict[str, Any] = Field(default_factory=dict)
    paper_tags: list[str] = Field(default_factory=list)
    tag_result: dict[str, Any] = Field(default_factory=dict)
    compare_dimensions: list[str] = Field(default_factory=list)
    formatted_references: list[str] = Field(default_factory=list)
    enable_judge: bool = True
    evidences: list[EvidenceSpan] = Field(default_factory=list)
    answer: str | None = None
    related_work: dict[str, Any] = Field(default_factory=dict)
    comparison: dict[str, Any] = Field(default_factory=dict)
    paper_facts: dict[str, dict[str, Any]] = Field(default_factory=dict)
    bibtex: dict[str, Any] = Field(default_factory=dict)
    human_review: dict[str, Any] = Field(default_factory=dict)
    route_after_judge: str | None = None
    route_after_human_review: str | None = None
    human_review_decision: str | None = None
    human_review_note: str | None = None
    final_answer: str | None = None
    artifacts: list[dict[str, Any]] = Field(default_factory=list)
    judge_results: list[dict[str, Any]] = Field(default_factory=list)
    trajectory_judge_result: dict[str, Any] | None = None
    revise_count: int = 0
    max_revise: int = 1
    prompt_overrides: dict[str, Any] = Field(default_factory=dict)
    rubric: dict[str, Any] = Field(default_factory=dict)
    intent_route: str | None = None
    compute_requested: bool = False
    compute_task: str | None = None
    table_uri: str | None = None
    analysis_code: str | None = None
    plot_kind: str | None = None
    plot_x: str | None = None
    plot_y: str | None = None
    task_id: str | None = None
    checkpoints: list[dict[str, Any]] = Field(default_factory=list)
    request_started: bool = False
    request_finished: bool = False
    llm_meta: dict[str, Any] | None = None
    observability_summary: dict[str, Any] | None = None
    trajectory_judge_reserved: bool = False
    recovery_mode: str | None = None
    resumed_from_checkpoint: str | None = None
    runtime: dict[str, Any] | None = None
    model: dict[str, Any] | None = None
    prompt: dict[str, Any] | None = None
    errors: list[str] = Field(default_factory=list)
    messages: list[dict[str, str]] = Field(default_factory=list)
    trace_id: str | None = None
