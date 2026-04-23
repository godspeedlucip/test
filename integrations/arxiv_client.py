from domain.paper import Author, PaperMetadata


class MockArxivClient:
    def resolve(self, query: str) -> PaperMetadata:
        return PaperMetadata(
            paper_id="arxiv:mock-001",
            title=f"ArXiv resolved: {query}",
            authors=[Author(name="Arxiv Author")],
            arxiv_id="mock-001",
            source="arxiv",
            pdf_url="https://arxiv.org/pdf/mock-001.pdf",
        )


arxiv_client = MockArxivClient()


def get_arxiv_client() -> MockArxivClient:
    return arxiv_client
