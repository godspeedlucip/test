from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from domain.context import RequestContext
from domain.document import ParsedFigure, ParsedSection, ParsedTable
from domain.runtime import RuntimeConfig
from integrations import get_object_store, get_repo
from tools.base import BaseToolHandler, failed_result, make_tool_error, success_result


class ParsePdfInput(BaseModel):
    context: RequestContext
    runtime: RuntimeConfig | None = None
    document_id: str
    parser_mode: Literal["fast", "balanced", "high_accuracy"] = "balanced"


class ParsePdfOutputData(BaseModel):
    document_id: str
    title: str | None = None
    abstract: str | None = None
    sections: list[ParsedSection] = Field(default_factory=list)
    tables: list[ParsedTable] = Field(default_factory=list)
    figures: list[ParsedFigure] = Field(default_factory=list)
    references_count: int = 0
    pages_count: int | None = None
    parse_status: Literal["completed", "partial", "failed"]


class ParsePdfHandler(BaseToolHandler):
    tool_name = "parse_pdf"
    input_model = ParsePdfInput
    output_model = ParsePdfOutputData

    def run(self, payload: ParsePdfInput):
        repo = get_repo()
        record = repo.documents.get(payload.document_id)
        if record is None:
            return failed_result(
                tool_name=self.tool_name,
                error=make_tool_error(code="document_not_found", message=f"document {payload.document_id} not found"),
            )
        content = get_object_store().get(record.storage_uri).decode("utf-8", errors="ignore")
        sections = [
            ParsedSection(title="Abstract", level=1, start_page=1, end_page=1),
            ParsedSection(title="Method", level=1, start_page=2, end_page=3),
            ParsedSection(title="Results", level=1, start_page=4, end_page=5),
        ]
        output = ParsePdfOutputData(
            document_id=payload.document_id,
            title=(repo.papers.get(record.paper_id).title if record.paper_id in repo.papers else "Mock Paper"),
            abstract=content[:120],
            sections=sections,
            tables=[],
            figures=[],
            references_count=5,
            pages_count=5,
            parse_status="completed",
        )
        record.sections = output.sections
        record.tables = output.tables
        record.figures = output.figures
        record.pages_count = output.pages_count
        record.parse_status = output.parse_status
        return success_result(tool_name=self.tool_name, data=output)


parse_pdf_tool = ParsePdfHandler()
