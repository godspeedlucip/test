from domain.base import ToolError, ToolMeta, ToolResult
from domain.context import RequestContext
from domain.document import DocumentRecord
from domain.paper import Author, PaperMetadata
from graph.nodes.prepare_documents import prepare_documents
from integrations import get_repo
from tools.document.fetch_pdf import FetchPdfInput, fetch_pdf_tool
from tools.document.index_document import IndexDocumentInput, index_document_tool
from tools.document.parse_pdf import ParsePdfInput, parse_pdf_tool


def _seed_paper(paper_id: str = "oa-test-1") -> str:
    repo = get_repo()
    repo.papers[paper_id] = PaperMetadata(
        paper_id=paper_id,
        title="Test Paper",
        authors=[Author(name="Author A")],
        abstract="test",
        year=2024,
        venue="TestConf",
        source="openalex",
        pdf_url=None,
    )
    return paper_id


def test_prepare_documents_skips_fetch_parse_index_when_already_indexed(monkeypatch):
    repo = get_repo()
    paper_id = _seed_paper("oa-ready")
    repo.documents["doc-ready"] = DocumentRecord(
        document_id="doc-ready",
        paper_id=paper_id,
        storage_uri="memory://object_store/doc-ready/file.txt",
        parse_status="completed",
        index_status="completed",
    )

    called = {"fetch": 0, "parse": 0, "index": 0}
    monkeypatch.setattr(
        fetch_pdf_tool,
        "execute",
        lambda payload: (
            called.__setitem__("fetch", called["fetch"] + 1)
            or ToolResult(success=False, error=ToolError(code="unexpected", message="fetch called"), meta=ToolMeta(tool_name="fetch_pdf"))
        ),
    )
    monkeypatch.setattr(
        parse_pdf_tool,
        "execute",
        lambda payload: (
            called.__setitem__("parse", called["parse"] + 1)
            or ToolResult(success=False, error=ToolError(code="unexpected", message="parse called"), meta=ToolMeta(tool_name="parse_pdf"))
        ),
    )
    monkeypatch.setattr(
        index_document_tool,
        "execute",
        lambda payload: (
            called.__setitem__("index", called["index"] + 1)
            or ToolResult(success=False, error=ToolError(code="unexpected", message="index called"), meta=ToolMeta(tool_name="index_document"))
        ),
    )

    out = prepare_documents(
        {
            "context": RequestContext(user_id="u1", request_id="prep-ready").model_dump(),
            "paper_ids": [paper_id],
            "document_ids": ["doc-ready"],
        }
    )
    assert "doc-ready" in out.get("working_document_ids", [])
    assert called == {"fetch": 0, "parse": 0, "index": 0}


def test_prepare_documents_unparsed_document_only_parses_and_indexes(monkeypatch):
    repo = get_repo()
    paper_id = _seed_paper("oa-unparsed")
    ctx = RequestContext(user_id="u1", request_id="prep-unparsed")
    fetched = fetch_pdf_tool.execute(FetchPdfInput(context=ctx, paper_id=paper_id))
    doc_id = fetched.data["document_id"]
    repo.documents[doc_id].parse_status = "not_started"
    repo.documents[doc_id].index_status = "not_started"

    called = {"fetch": 0, "parse": 0, "index": 0}
    original_parse = parse_pdf_tool.execute
    original_index = index_document_tool.execute

    monkeypatch.setattr(
        fetch_pdf_tool,
        "execute",
        lambda payload: called.__setitem__("fetch", called["fetch"] + 1),
    )

    def wrapped_parse(payload):
        called["parse"] += 1
        return original_parse(payload)

    def wrapped_index(payload):
        called["index"] += 1
        return original_index(payload)

    monkeypatch.setattr(parse_pdf_tool, "execute", wrapped_parse)
    monkeypatch.setattr(index_document_tool, "execute", wrapped_index)

    out = prepare_documents(
        {
            "context": ctx.model_dump(),
            "paper_ids": [paper_id],
            "document_ids": [doc_id],
        }
    )
    assert doc_id in out.get("working_document_ids", [])
    assert called["fetch"] == 0
    assert called["parse"] == 1
    assert called["index"] == 1


def test_prepare_documents_new_document_fetch_parse_index():
    paper_id = _seed_paper("oa-new")
    ctx = RequestContext(user_id="u1", request_id="prep-new")
    out = prepare_documents(
        {
            "context": ctx.model_dump(),
            "paper_ids": [paper_id],
            "document_ids": [],
        }
    )
    assert out.get("working_document_ids")
    doc_id = out["working_document_ids"][0]
    rec = get_repo().documents[doc_id]
    assert rec.parse_status == "completed"
    assert rec.index_status == "completed"


def test_prepare_documents_records_execution_and_error_on_failure(monkeypatch):
    paper_id = _seed_paper("oa-fail")
    ctx = RequestContext(user_id="u1", request_id="prep-fail")

    def fail_parse(_payload):
        return ToolResult(
            success=False,
            error=ToolError(code="parse_failed", message="broken parse", error_layer="tool"),
            meta=ToolMeta(tool_name="parse_pdf"),
        )

    monkeypatch.setattr(parse_pdf_tool, "execute", fail_parse)
    out = prepare_documents(
        {
            "context": ctx.model_dump(),
            "paper_ids": [paper_id],
            "document_ids": [],
        }
    )
    assert out.get("errors")
    assert any("parse_pdf" in e for e in out.get("errors", []))
    assert any(step.get("selected_tool") == "parse_pdf" for step in out.get("execution_steps", []))
