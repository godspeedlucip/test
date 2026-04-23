from typing import Literal

from pydantic import BaseModel, Field


class DocumentAnchor(BaseModel):
    document_id: str
    paper_id: str | None = None
    page_no: int | None = None
    section_title: str | None = None
    chunk_id: str | None = None
    char_start: int | None = None
    char_end: int | None = None


class ParsedSection(BaseModel):
    title: str
    level: int
    start_page: int | None = None
    end_page: int | None = None


class ParsedTable(BaseModel):
    table_id: str
    title: str | None = None
    page_no: int | None = None
    csv_uri: str | None = None


class ParsedFigure(BaseModel):
    figure_id: str
    caption: str | None = None
    page_no: int | None = None
    image_uri: str | None = None


class DocumentRecord(BaseModel):
    document_id: str
    paper_id: str | None = None
    storage_uri: str
    file_name: str | None = None
    checksum: str | None = None
    source_url: str | None = None
    parse_status: Literal["not_started", "completed", "partial", "failed"] = "not_started"
    index_status: Literal["not_started", "completed", "partial", "failed"] = "not_started"
    sections: list[ParsedSection] = Field(default_factory=list)
    tables: list[ParsedTable] = Field(default_factory=list)
    figures: list[ParsedFigure] = Field(default_factory=list)
    pages_count: int | None = None
