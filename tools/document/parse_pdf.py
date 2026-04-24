from __future__ import annotations

import math
import re
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


_SECTION_PATTERN = re.compile(
    r"^(abstract|introduction|background|related work|method|methods|approach|experiment|results|discussion|conclusion|references)\b",
    flags=re.IGNORECASE,
)
_NUMBERED_PATTERN = re.compile(r"^\d+(\.\d+)*\s+[A-Za-z].{0,120}$")


def _extract_text(raw: bytes) -> str:
    if raw.startswith(b"%PDF"):
        decoded = raw.decode("latin1", errors="ignore")
        candidates = re.findall(r"[A-Za-z0-9,\.\(\)\[\]:;'\-\/\s]{20,}", decoded)
        text = "\n".join(x.strip() for x in candidates if x.strip())
        if text.strip():
            return text
    text = raw.decode("utf-8", errors="ignore").strip()
    if text:
        return text
    return raw.decode("latin1", errors="ignore")


def _normalize_lines(text: str) -> list[str]:
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    return [line for line in lines if line]


def _estimate_page_from_line(line_idx: int, total_lines: int, pages: int) -> int:
    if total_lines <= 0:
        return 1
    bucket = int((line_idx / total_lines) * pages)
    return max(1, min(pages, bucket + 1))


def _detect_sections(lines: list[str], pages_count: int) -> list[ParsedSection]:
    if not lines:
        return []
    found: list[tuple[str, int]] = []
    for idx, line in enumerate(lines):
        looks_like_heading = bool(_SECTION_PATTERN.match(line) or _NUMBERED_PATTERN.match(line))
        if looks_like_heading and len(line) <= 140:
            found.append((line, idx))
    if not found:
        return []

    sections: list[ParsedSection] = []
    total_lines = len(lines)
    for pos, (title, start_idx) in enumerate(found):
        end_idx = found[pos + 1][1] - 1 if pos + 1 < len(found) else total_lines - 1
        start_page = _estimate_page_from_line(start_idx, total_lines, pages_count)
        end_page = _estimate_page_from_line(end_idx, total_lines, pages_count)
        sections.append(
            ParsedSection(
                title=title[:200],
                level=1,
                start_page=start_page,
                end_page=max(start_page, end_page),
            )
        )
    return sections


def _build_abstract(lines: list[str], sections: list[ParsedSection]) -> str | None:
    if not lines:
        return None
    abstract_candidates: list[str] = []
    for idx, line in enumerate(lines):
        if line.lower().startswith("abstract"):
            abstract_candidates.extend(lines[idx + 1 : idx + 6])
            break
    if not abstract_candidates and sections:
        abstract_candidates = lines[: min(6, len(lines))]
    abstract = " ".join(abstract_candidates).strip()
    if abstract:
        return abstract[:1200]
    return None


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
        raw = get_object_store().get(record.storage_uri)
        text = _extract_text(raw)
        lines = _normalize_lines(text)
        pages_count = max(1, math.ceil(max(1, len(text)) / 3200))
        sections = _detect_sections(lines, pages_count=pages_count)
        parse_status: Literal["completed", "partial", "failed"] = "completed" if lines else "failed"
        if lines and not sections:
            parse_status = "partial"
        title = lines[0][:300] if lines else None
        output = ParsePdfOutputData(
            document_id=payload.document_id,
            title=title,
            abstract=_build_abstract(lines, sections),
            sections=sections,
            tables=[],
            figures=[],
            references_count=len([line for line in lines if "doi" in line.lower() or line.lower().startswith("[")]),
            pages_count=pages_count,
            parse_status=parse_status,
        )
        record.sections = output.sections
        record.tables = output.tables
        record.figures = output.figures
        record.pages_count = output.pages_count
        record.parse_status = output.parse_status
        return success_result(tool_name=self.tool_name, data=output)


parse_pdf_tool = ParsePdfHandler()
