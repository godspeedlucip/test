from domain.context import RequestContext
from tools.academic.search_papers import SearchPapersInput, search_papers_tool
from tools.citation.export_bibtex import ExportBibtexInput, export_bibtex_tool
from tools.document.fetch_pdf import FetchPdfInput, fetch_pdf_tool
from tools.document.index_document import IndexDocumentInput, index_document_tool
from tools.document.parse_pdf import ParsePdfInput, parse_pdf_tool
from tools.synthesis.compare_papers import ComparePapersInput, compare_papers_tool
from tools.synthesis.extract_paper_facts import ExtractPaperFactsInput, extract_paper_facts_tool


def test_extract_compare_and_export_have_phase1_outputs():
    ctx = RequestContext(user_id="u-cmp", request_id="trace-cmp-export")
    search = search_papers_tool.execute(SearchPapersInput(context=ctx, query="transformer", top_k=2))
    paper_ids = [p["paper_id"] for p in search.data["papers"][:2]]

    document_ids = []
    facts_by_paper = {}
    for paper_id in paper_ids:
        fetched = fetch_pdf_tool.execute(FetchPdfInput(context=ctx, paper_id=paper_id))
        parse_pdf_tool.execute(ParsePdfInput(context=ctx, document_id=fetched.data["document_id"]))
        index_document_tool.execute(IndexDocumentInput(context=ctx, document_id=fetched.data["document_id"]))
        fact = extract_paper_facts_tool.execute(
            ExtractPaperFactsInput(context=ctx, document_id=fetched.data["document_id"], dimensions=["method", "dataset", "metrics"])
        )
        assert fact.success
        assert fact.data["facts"]["evidence_map"]
        assert fact.meta.model_name
        assert fact.meta.prompt_version
        assert fact.meta.token_usage
        document_ids.append(fetched.data["document_id"])
        facts_by_paper[paper_id] = fact.data["facts"]

    compared = compare_papers_tool.execute(
        ComparePapersInput(
            context=ctx,
            paper_ids=paper_ids,
            document_ids=document_ids,
            facts_by_paper=facts_by_paper,
            require_evidence=True,
        )
    )
    assert compared.success
    assert compared.data["summary"]
    assert compared.meta.model_name
    assert compared.meta.prompt_version
    assert compared.meta.token_usage

    exported = export_bibtex_tool.execute(ExportBibtexInput(context=ctx, paper_ids=paper_ids))
    assert exported.success
    assert exported.data["export_file_uri"].startswith("file://")
    assert "memory://" not in exported.data["export_file_uri"]
