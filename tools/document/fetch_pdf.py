from __future__ import annotations

from pydantic import BaseModel

from domain.context import RequestContext
from domain.runtime import RuntimeConfig
from integrations import get_object_store, get_repo
from tools.base import BaseToolHandler, failed_result, make_tool_error, success_result


class FetchPdfInput(BaseModel):
    context: RequestContext
    runtime: RuntimeConfig | None = None
    paper_id: str | None = None
    doi: str | None = None
    pdf_url: str | None = None


class FetchPdfOutputData(BaseModel):
    document_id: str
    storage_uri: str
    file_name: str | None = None
    checksum: str | None = None
    source_url: str | None = None


class FetchPdfHandler(BaseToolHandler):
    tool_name = "fetch_pdf"
    input_model = FetchPdfInput
    output_model = FetchPdfOutputData

    def run(self, payload: FetchPdfInput):
        if not any([payload.paper_id, payload.doi, payload.pdf_url]):
            return failed_result(
                tool_name=self.tool_name,
                error=make_tool_error(code="invalid_input", message="One of paper_id/doi/pdf_url is required"),
            )
        store = get_object_store()
        text = f"Mock PDF content for {payload.paper_id or payload.doi or payload.pdf_url}".encode("utf-8")
        file_name = f"{payload.paper_id or 'paper'}.pdf"
        storage_uri, checksum = store.put(text, file_name)
        document_id = storage_uri.split("/")[3]

        from domain.document import DocumentRecord

        get_repo().documents[document_id] = DocumentRecord(
            document_id=document_id,
            paper_id=payload.paper_id,
            storage_uri=storage_uri,
            file_name=file_name,
            checksum=checksum,
            source_url=payload.pdf_url,
        )
        return success_result(
            tool_name=self.tool_name,
            data=FetchPdfOutputData(
                document_id=document_id,
                storage_uri=storage_uri,
                file_name=file_name,
                checksum=checksum,
                source_url=payload.pdf_url,
            ),
        )


fetch_pdf_tool = FetchPdfHandler()
