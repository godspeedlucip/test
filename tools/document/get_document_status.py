from pydantic import BaseModel

from domain.context import RequestContext
from domain.runtime import RuntimeConfig
from integrations import get_repo
from tools.base import BaseToolHandler, failed_result, make_tool_error, success_result


class GetDocumentStatusInput(BaseModel):
    context: RequestContext
    runtime: RuntimeConfig | None = None
    document_id: str | None = None
    paper_id: str | None = None


class GetDocumentStatusOutputData(BaseModel):
    exists: bool
    document_id: str | None = None
    paper_id: str | None = None
    parse_status: str
    index_status: str
    pages_count: int | None = None
    parsed: bool = False
    indexed: bool = False


class GetDocumentStatusHandler(BaseToolHandler):
    tool_name = "get_document_status"
    input_model = GetDocumentStatusInput
    output_model = GetDocumentStatusOutputData

    def run(self, payload: GetDocumentStatusInput):
        if not payload.document_id and not payload.paper_id:
            return failed_result(
                tool_name=self.tool_name,
                error=make_tool_error(code="invalid_input", message="document_id or paper_id is required"),
            )

        repo = get_repo()
        document_id = payload.document_id
        record = repo.documents.get(document_id) if document_id else None
        if record is None and payload.paper_id:
            for doc_id, candidate in repo.documents.items():
                if candidate.paper_id == payload.paper_id:
                    record = candidate
                    document_id = doc_id
                    break

        if record is None:
            return success_result(
                tool_name=self.tool_name,
                data=GetDocumentStatusOutputData(
                    exists=False,
                    document_id=document_id,
                    paper_id=payload.paper_id,
                    parse_status="missing",
                    index_status="missing",
                    pages_count=None,
                    parsed=False,
                    indexed=False,
                ),
            )

        parsed = record.parse_status == "completed"
        indexed = record.index_status == "completed"
        return success_result(
            tool_name=self.tool_name,
            data=GetDocumentStatusOutputData(
                exists=True,
                document_id=document_id,
                paper_id=record.paper_id or payload.paper_id,
                parse_status=record.parse_status,
                index_status=record.index_status,
                pages_count=record.pages_count,
                parsed=parsed,
                indexed=indexed,
            ),
        )


get_document_status_tool = GetDocumentStatusHandler()
