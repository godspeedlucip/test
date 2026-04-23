from domain.context import RequestContext
from tools.document.fetch_pdf import FetchPdfInput, fetch_pdf_tool
from tools.document.get_document_status import GetDocumentStatusInput, get_document_status_tool
from tools.document.index_document import IndexDocumentInput, index_document_tool
from tools.document.parse_pdf import ParsePdfInput, parse_pdf_tool

from graph.nodes.common import run_node


def prepare_documents(state: dict):
    def _impl(s: dict):
        ctx = RequestContext.model_validate(s.get("context", {"user_id": "anonymous"}))
        paper_ids = s.get("paper_ids") or []
        document_ids = s.get("document_ids") or []
        if not paper_ids and not document_ids:
            return {}
        new_docs = list(document_ids)
        for paper_id in paper_ids:
            fr = fetch_pdf_tool.execute(FetchPdfInput(context=ctx, paper_id=paper_id))
            if not fr.success:
                continue
            doc_id = fr.data["document_id"]
            status = get_document_status_tool.execute(GetDocumentStatusInput(context=ctx, document_id=doc_id))
            if status.success and status.data["parse_status"] != "completed":
                parse_pdf_tool.execute(ParsePdfInput(context=ctx, document_id=doc_id))
            if status.success and status.data["index_status"] != "completed":
                index_document_tool.execute(IndexDocumentInput(context=ctx, document_id=doc_id))
            new_docs.append(doc_id)
        return {"document_ids": list(dict.fromkeys(new_docs))}

    return run_node("prepare_documents", state, _impl)
