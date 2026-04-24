from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from domain.context import RequestContext
from domain.paper import PaperMetadata
from domain.runtime import RuntimeConfig
from integrations import get_openalex_client, get_repo
from integrations.openalex_client import OpenAlexClientError
from integrations.provider_errors import ProviderFailureError
from tools.base import BaseToolHandler, failed_result, make_tool_error, success_result, wrap_exception


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
        try:
            papers = get_openalex_client().search(
                payload.query,
                authors=payload.authors,
                year_from=payload.year_from,
                year_to=payload.year_to,
                venue=payload.venue,
                top_k=payload.top_k,
                sort_by=payload.sort_by,
                sources=payload.sources,
            )
            repo = get_repo()
            for paper in papers:
                repo.papers[paper.paper_id] = paper
            return success_result(
                tool_name=self.tool_name,
                data=SearchPapersOutputData(query=payload.query, total=len(papers), papers=papers),
            )
        except Exception as exc:
            if isinstance(exc, ProviderFailureError):
                return failed_result(tool_name=self.tool_name, error=exc.tool_error)
            if isinstance(exc, OpenAlexClientError):
                return failed_result(
                    tool_name=self.tool_name,
                    error=make_tool_error(
                        code="PROVIDER_FAILURE",
                        message="Real provider failed",
                        error_layer="network" if exc.error_layer == "network" else exc.error_layer,
                        detail={"status_code": exc.status_code} if exc.status_code else None,
                        retryable=exc.error_layer == "network",
                    ),
                )
            return failed_result(tool_name=self.tool_name, error=wrap_exception(self.tool_name, exc))


search_papers_tool = SearchPapersHandler()
