import os

import pytest

from integrations import openalex_client as openalex_client_module
from integrations.openalex_client import RealOpenAlexClient


@pytest.mark.external
def test_openalex_real_client_search_external():
    if os.getenv("RUN_EXTERNAL_TESTS", "0") != "1":
        pytest.skip("set RUN_EXTERNAL_TESTS=1 to run external OpenAlex test")
    client = RealOpenAlexClient()
    papers = client.search("retrieval augmented generation", top_k=2, sort_by="relevance")
    assert len(papers) >= 1
    assert papers[0].paper_id


def test_prod_mode_requires_real_provider(monkeypatch):
    monkeypatch.setenv("RUNTIME_ENV", "prod")
    monkeypatch.setenv("ACADEMIC_PROVIDER_MODE", "mock")
    openalex_client_module.openalex_client = None
    with pytest.raises(RuntimeError):
        openalex_client_module.build_openalex_client()
