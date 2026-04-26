from __future__ import annotations

import os

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


class RealCrossrefClient:
    def get_details(self, doi: str) -> PaperMetadata:
        raise RuntimeError("Real Crossref provider is not wired in this repository yet")


class HybridCrossrefClient:
    def __init__(self, primary, fallback) -> None:
        self.primary = primary
        self.fallback = fallback

    def get_details(self, doi: str) -> PaperMetadata:
        try:
            return self.primary.get_details(doi)
        except Exception:
            return self.fallback.get_details(doi)


crossref_client = None


def build_crossref_client():
    mode = os.getenv("ACADEMIC_PROVIDER_MODE", "mock").lower()
    if mode == "real":
        return RealCrossrefClient()
    if mode == "hybrid":
        return HybridCrossrefClient(RealCrossrefClient(), MockCrossrefClient())
    return MockCrossrefClient()


def get_crossref_client():
    global crossref_client
    if crossref_client is None:
        crossref_client = build_crossref_client()
    return crossref_client
