from __future__ import annotations

from dataclasses import dataclass, field

from domain.document import DocumentRecord
from domain.paper import PaperMetadata


@dataclass
class InMemoryRepository:
    papers: dict[str, PaperMetadata] = field(default_factory=dict)
    documents: dict[str, DocumentRecord] = field(default_factory=dict)
    chunks: dict[str, list[dict]] = field(default_factory=dict)
    library: dict[str, list[str]] = field(default_factory=dict)
    notes: dict[str, list[str]] = field(default_factory=dict)


repo = InMemoryRepository()


def get_repo() -> InMemoryRepository:
    return repo
