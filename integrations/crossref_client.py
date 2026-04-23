from __future__ import annotations

from domain.paper import Author, PaperMetadata


class MockCrossrefClient:
    def get_details(self, doi: str) -> PaperMetadata:
        return PaperMetadata(
            paper_id=f"doi:{doi}",
            title=f"Crossref record for {doi}",
            authors=[Author(name="Crossref Author")],
            doi=doi,
            source="crossref",
            year=2023,
        )


crossref_client = MockCrossrefClient()


def get_crossref_client() -> MockCrossrefClient:
    return crossref_client
