from domain.context import RequestContext
from tools.academic.search_papers import SearchPapersInput, search_papers_tool
from tools.document.fetch_pdf import FetchPdfInput, fetch_pdf_tool
from tools.document.index_document import IndexDocumentInput, index_document_tool
from tools.document.parse_pdf import ParsePdfInput, parse_pdf_tool
from tools.document.retrieve_evidence import RetrieveEvidenceInput, retrieve_evidence_tool


def test_document_parse_chunk_index_retrieve_loop():
    ctx = RequestContext(user_id="u-loop", request_id="trace-doc-loop")
    search = search_papers_tool.execute(SearchPapersInput(context=ctx, query="retrieval", top_k=1))
    paper_id = search.data["papers"][0]["paper_id"]

    fetched = fetch_pdf_tool.execute(FetchPdfInput(context=ctx, paper_id=paper_id))
    assert fetched.success
    assert fetched.data["storage_uri"]

    parsed = parse_pdf_tool.execute(ParsePdfInput(context=ctx, document_id=fetched.data["document_id"]))
    assert parsed.success
    assert parsed.data["parse_status"] in {"completed", "partial"}
    assert parsed.data["title"]

    indexed = index_document_tool.execute(IndexDocumentInput(context=ctx, document_id=fetched.data["document_id"], chunk_size=300))
    assert indexed.success
    assert indexed.data["chunks_count"] > 0

    retrieved = retrieve_evidence_tool.execute(
        RetrieveEvidenceInput(
            context=ctx,
            document_id=fetched.data["document_id"],
            query="method retrieval",
            top_k=3,
        )
    )
    assert retrieved.success
    assert len(retrieved.data["evidences"]) >= 1
    scores = [ev["score"] for ev in retrieved.data["evidences"]]
    assert scores == sorted(scores, reverse=True)
