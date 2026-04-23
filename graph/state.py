from __future__ import annotations

from typing import Any, TypedDict


class GraphState(TypedDict, total=False):
    user_query: str
    context: dict[str, Any]
    paper_ids: list[str]
    document_ids: list[str]
    question: str
    compare_dimensions: list[str]
    enable_judge: bool
    model: dict[str, Any]
    prompt: dict[str, Any]
    rubric: dict[str, Any]
    answer: str
    evidences: list[dict[str, Any]]
    comparison: dict[str, Any]
    bibtex: dict[str, Any]
    final_answer: str
    artifacts: list[dict[str, Any]]
    judge_results: list[dict[str, Any]]
    trace_id: str
    errors: list[str]
