from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from domain.context import RequestContext
from domain.evidence import EvidenceSpan
from domain.runtime import ModelConfig, PromptConfig, RuntimeConfig
from integrations import get_repo
from tools.base import BaseToolHandler, success_result


class ComparisonRow(BaseModel):
    paper_id: str
    title: str
    values: dict[str, Any]
    evidence_map: dict[str, list[EvidenceSpan]] = Field(default_factory=dict)


class ComparePapersInput(BaseModel):
    context: RequestContext
    model: ModelConfig | None = None
    prompt: PromptConfig | None = None
    runtime: RuntimeConfig | None = None
    paper_ids: list[str]
    document_ids: list[str]
    dimensions: list[str] = Field(default_factory=lambda: ["method", "dataset", "metrics", "limitations"])
    output_format: Literal["paragraph", "table", "both"] = "both"
    require_evidence: bool = True


class ComparePapersOutputData(BaseModel):
    summary: str
    table: list[ComparisonRow] = Field(default_factory=list)
    key_differences: list[str] = Field(default_factory=list)
    common_patterns: list[str] = Field(default_factory=list)


class ComparePapersHandler(BaseToolHandler):
    tool_name = "compare_papers"
    input_model = ComparePapersInput
    output_model = ComparePapersOutputData

    def run(self, payload: ComparePapersInput):
        repo = get_repo()
        rows: list[ComparisonRow] = []
        for paper_id in payload.paper_ids:
            paper = repo.papers.get(paper_id)
            title = paper.title if paper else paper_id
            values = {dim: f"mock_{dim}_{paper_id}" for dim in payload.dimensions}
            rows.append(ComparisonRow(paper_id=paper_id, title=title, values=values))
        summary = f"Compared {len(rows)} papers across {len(payload.dimensions)} dimensions."
        return success_result(
            tool_name=self.tool_name,
            data=ComparePapersOutputData(
                summary=summary,
                table=rows,
                key_differences=["Different methods", "Different metrics"],
                common_patterns=["Most use benchmark datasets"],
            ),
        )


compare_papers_tool = ComparePapersHandler()
