from __future__ import annotations

import time
import uuid

from domain.context import RequestContext
from domain.observability import ObservabilityEvent
from tools.academic.get_paper_details import GetPaperDetailsInput, get_paper_details_tool
from tools.document.fetch_pdf import FetchPdfInput, fetch_pdf_tool
from tools.document.get_document_status import GetDocumentStatusInput, get_document_status_tool
from tools.document.index_document import IndexDocumentInput, index_document_tool
from tools.observability.record_observability_event import (
    RecordObservabilityEventInput,
    record_observability_event_tool,
)
from tools.document.parse_pdf import ParsePdfInput, parse_pdf_tool

from graph.nodes.common import run_node


def prepare_documents(state: dict):
    def _impl(s: dict):
        ctx = RequestContext.model_validate(s.get("context", {"user_id": "anonymous"}))
        paper_ids = list(s.get("paper_ids") or [])
        document_ids = s.get("document_ids") or []
        paper_details = dict(s.get("paper_details") or {})
        execution_steps = list(s.get("execution_steps") or [])
        errors = list(s.get("errors") or [])

        if not paper_ids and not document_ids:
            return {}

        new_docs: list[str] = []
        working_document_ids: list[str] = []

        def _record_prepare_error(paper_id: str | None, stage: str, message: str) -> None:
            trace_id = s.get("trace_id") or ctx.request_id or "unknown"
            errors.append(f"prepare_documents[{paper_id or 'unknown'}][{stage}]: {message}")
            execution_steps.append(
                {
                    "step_id": f"prepare:{paper_id or 'unknown'}:{stage}",
                    "node_name": "prepare_documents",
                    "status": "failed",
                    "selected_tool": stage,
                    "tool_input_summary": {"paper_id": paper_id},
                    "tool_output_summary": None,
                    "error_message": message,
                }
            )
            record_observability_event_tool.execute(
                RecordObservabilityEventInput(
                    context=ctx,
                    event=ObservabilityEvent(
                        event_type="error_raised",
                        trace_id=trace_id,
                        span_id=str(uuid.uuid4()),
                        parent_span_id=None,
                        timestamp_ms=int(time.time() * 1000),
                        payload={
                            "node_name": "prepare_documents",
                            "paper_id": paper_id,
                            "stage": stage,
                            "message": message,
                        },
                    ),
                )
            )

        total_items = max(len(paper_ids), len(document_ids))
        if total_items == 0:
            total_items = len(paper_ids) or len(document_ids)

        for idx in range(total_items):
            paper_id = paper_ids[idx] if idx < len(paper_ids) else None
            doc_hint = document_ids[idx] if idx < len(document_ids) else None

            if not paper_id and not doc_hint:
                continue

            pdf_url = None
            if paper_id:
                detail = get_paper_details_tool.execute(GetPaperDetailsInput(context=ctx, paper_id=paper_id))
                if detail.success:
                    paper_details[paper_id] = detail.data["paper"]
                    pdf_url = detail.data["paper"].get("pdf_url")

            status_result = get_document_status_tool.execute(
                GetDocumentStatusInput(context=ctx, document_id=doc_hint, paper_id=paper_id)
            )
            if not status_result.success:
                _record_prepare_error(
                    paper_id,
                    "get_document_status",
                    status_result.error.message if status_result.error else "get_document_status failed",
                )
                continue

            status_data = status_result.data
            doc_id = status_data.get("document_id")

            if not status_data.get("exists", False):
                if not paper_id:
                    _record_prepare_error(None, "fetch_pdf", "missing paper_id for fetch")
                    continue
                fetched = fetch_pdf_tool.execute(FetchPdfInput(context=ctx, paper_id=paper_id, pdf_url=pdf_url))
                if not fetched.success:
                    _record_prepare_error(
                        paper_id,
                        "fetch_pdf",
                        fetched.error.message if fetched.error else "fetch_pdf failed",
                    )
                    continue
                doc_id = fetched.data.get("document_id")
                status_result = get_document_status_tool.execute(
                    GetDocumentStatusInput(context=ctx, document_id=doc_id, paper_id=paper_id)
                )
                if not status_result.success:
                    _record_prepare_error(
                        paper_id,
                        "get_document_status",
                        status_result.error.message if status_result.error else "get_document_status failed",
                    )
                    continue
                status_data = status_result.data

            if not doc_id:
                _record_prepare_error(paper_id, "get_document_status", "resolved document_id is missing")
                continue

            if not status_data.get("parsed", False):
                parsed = parse_pdf_tool.execute(ParsePdfInput(context=ctx, runtime=s.get("runtime"), document_id=doc_id))
                if not parsed.success:
                    _record_prepare_error(
                        paper_id,
                        "parse_pdf",
                        parsed.error.message if parsed.error else "parse_pdf failed",
                    )
                    continue
                status_result = get_document_status_tool.execute(
                    GetDocumentStatusInput(context=ctx, document_id=doc_id, paper_id=paper_id)
                )
                if not status_result.success:
                    _record_prepare_error(
                        paper_id,
                        "get_document_status",
                        status_result.error.message if status_result.error else "get_document_status failed",
                    )
                    continue
                status_data = status_result.data

            if not status_data.get("indexed", False):
                indexed = index_document_tool.execute(
                    IndexDocumentInput(context=ctx, runtime=s.get("runtime"), document_id=doc_id)
                )
                if not indexed.success:
                    _record_prepare_error(
                        paper_id,
                        "index_document",
                        indexed.error.message if indexed.error else "index_document failed",
                    )
                    continue

            new_docs.append(doc_id)
            working_document_ids.append(doc_id)

        if not new_docs:
            if errors:
                return {
                    "paper_ids": paper_ids,
                    "paper_details": paper_details,
                    "document_ids": [],
                    "working_document_ids": [],
                    "execution_steps": execution_steps,
                    "errors": errors,
                }
            raise RuntimeError("prepare_documents: no document could be prepared")

        return {
            "paper_ids": paper_ids,
            "paper_details": paper_details,
            "document_ids": list(dict.fromkeys(new_docs)),
            "working_document_ids": list(dict.fromkeys(working_document_ids)),
            "execution_steps": execution_steps,
            "errors": errors,
        }

    return run_node("prepare_documents", state, _impl)
