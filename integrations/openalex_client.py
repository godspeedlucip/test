from __future__ import annotations

from domain.paper import Author, PaperMetadata


class MockOpenAlexClient:
    def search(self, query: str, top_k: int = 10) -> list[PaperMetadata]:
        return [
            PaperMetadata(
                paper_id=f"oa-{i}",
                title=f"{query} Study {i}",
                authors=[Author(name="Mock Author")],
                abstract=f"Abstract for {query} {i}",
                year=2024,
                venue="MockConf",
                source="openalex",
                pdf_url=f"https://example.org/{i}.pdf",
            )
            for i in range(1, top_k + 1)
        ]


openalex_client = MockOpenAlexClient()


def get_openalex_client() -> MockOpenAlexClient:
    return openalex_client
