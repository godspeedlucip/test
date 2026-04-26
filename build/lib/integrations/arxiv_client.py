from __future__ import annotations

import os

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


class RealArxivClient:
    def resolve(self, query: str) -> PaperMetadata:
        raise RuntimeError("Real ArXiv provider is not wired in this repository yet")


class HybridArxivClient:
    def __init__(self, primary, fallback) -> None:
        self.primary = primary
        self.fallback = fallback

    def resolve(self, query: str) -> PaperMetadata:
        try:
            return self.primary.resolve(query)
        except Exception:
            return self.fallback.resolve(query)


arxiv_client = None


def build_arxiv_client():
    mode = os.getenv("ACADEMIC_PROVIDER_MODE", "mock").lower()
    if mode == "real":
        return RealArxivClient()
    if mode == "hybrid":
        return HybridArxivClient(RealArxivClient(), MockArxivClient())
    return MockArxivClient()


def get_arxiv_client():
    global arxiv_client
    if arxiv_client is None:
        arxiv_client = build_arxiv_client()
    return arxiv_client
