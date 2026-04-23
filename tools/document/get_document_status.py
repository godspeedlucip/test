from pydantic import BaseModel

from domain.context import RequestContext
from domain.runtime import RuntimeConfig
from integrations import get_repo
from tools.base import BaseToolHandler, failed_result, make_tool_error, success_result


class GetDocumentStatusInput(BaseModel):
    context: RequestContext
    runtime: RuntimeConfig | None = None
    document_id: str


class GetDocumentStatusOutputData(BaseModel):
    document_id: str
    parse_status: str
    index_status: str
    pages_count: int | None = None


class GetDocumentStatusHandler(BaseToolHandler):
    tool_name = "get_document_status"
    input_model = GetDocumentStatusInput
    output_model = GetDocumentStatusOutputData

    def run(self, payload: GetDocumentStatusInput):
        record = get_repo().documents.get(payload.document_id)
        if record is None:
            return failed_result(
                tool_name=self.tool_name,
                error=make_tool_error(code="document_not_found", message=f"document {payload.document_id} not found"),
            )
        return success_result(
            tool_name=self.tool_name,
            data=GetDocumentStatusOutputData(
                document_id=payload.document_id,
                parse_status=record.parse_status,
                index_status=record.index_status,
                pages_count=record.pages_count,
            ),
        )


get_document_status_tool = GetDocumentStatusHandler()
