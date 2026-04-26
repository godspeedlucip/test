from pydantic import BaseModel


class CitationItem(BaseModel):
    paper_id: str
    title: str | None = None
    doi: str | None = None
    bibtex_key: str | None = None
    citation_text: str | None = None
