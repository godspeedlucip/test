from pydantic import BaseModel, Field


class Author(BaseModel):
    name: str
    affiliation: str | None = None
    orcid: str | None = None


class PaperMetadata(BaseModel):
    paper_id: str
    title: str
    authors: list[Author] = Field(default_factory=list)
    abstract: str | None = None
    year: int | None = None
    venue: str | None = None
    doi: str | None = None
    arxiv_id: str | None = None
    pdf_url: str | None = None
    source: str | None = None
    citation_count: int | None = None
    keywords: list[str] = Field(default_factory=list)
