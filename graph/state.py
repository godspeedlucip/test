from __future__ import annotations

from typing import Any, TypedDict


class GraphState(TypedDict, total=False):
    workflow: str
    user_query: str
    topic: str
    plan: list[str]
    context: dict[str, Any]
    paper_ids: list[str]
    document_ids: list[str]
    question: str
    compare_dimensions: list[str]
    enable_judge: bool
    max_revise: int
    revise_count: int
    max_retries: int
    route_after_judge: str
    runtime: dict[str, Any]
    model: dict[str, Any]
    prompt: dict[str, Any]
    rubric: dict[str, Any]
    query: str
    top_k: int
    paper_id: str
    library_candidates: list[dict[str, Any]]
    library_search_result: dict[str, Any]
    selected_paper_id: str
    saved_paper_id: str
    save_result: dict[str, Any]
    answer: str
    evidences: list[dict[str, Any]]
    paper_facts: dict[str, dict[str, Any]]
    comparison: dict[str, Any]
    related_work: dict[str, Any]
    trajectory_judge_result: dict[str, Any]
    human_review: dict[str, Any]
    bibtex: dict[str, Any]
    final_answer: str
    artifacts: list[dict[str, Any]]
    execution_steps: list[dict[str, Any]]
    checkpoints: list[dict[str, Any]]
    judge_results: list[dict[str, Any]]
    request_started: bool
    request_finished: bool
    trace_id: str
    errors: list[str]
