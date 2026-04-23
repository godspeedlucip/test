from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from domain.context import RequestContext
from domain.paper import PaperMetadata
from domain.runtime import RuntimeConfig
from integrations import get_openalex_client, get_repo
from tools.base import BaseToolHandler, success_result


class SearchPapersInput(BaseModel):
    context: RequestContext
    runtime: RuntimeConfig | None = None
    query: str
    authors: list[str] = Field(default_factory=list)
    year_from: int | None = None
    year_to: int | None = None
    venue: str | None = None
    sources: list[str] = Field(default_factory=lambda: ["openalex", "crossref", "arxiv"])
    top_k: int = 10
    sort_by: Literal["relevance", "date", "citations"] = "relevance"
    include_abstract: bool = True


class SearchPapersOutputData(BaseModel):
    query: str
    total: int
    papers: list[PaperMetadata]


class SearchPapersHandler(BaseToolHandler):
    tool_name = "search_papers"
    input_model = SearchPapersInput
    output_model = SearchPapersOutputData

    def run(self, payload: SearchPapersInput):
        papers = get_openalex_client().search(payload.query, top_k=payload.top_k)
        repo = get_repo()
        for paper in papers:
            repo.papers[paper.paper_id] = paper
        return success_result(
            tool_name=self.tool_name,
            data=SearchPapersOutputData(query=payload.query, total=len(papers), papers=papers),
        )


search_papers_tool = SearchPapersHandler()
