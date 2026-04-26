from pydantic import BaseModel

from domain.context import RequestContext
from integrations import get_java_client
from integrations.java_client import AddPaperNoteRequest, JavaClientError
from integrations.provider_errors import ProviderFailureError
from tools.base import BaseToolHandler, failed_result, make_tool_error, success_result, wrap_exception


class AddPaperNoteInput(BaseModel):
    context: RequestContext
    paper_id: str
    note: str


class AddPaperNoteOutputData(BaseModel):
    added: bool


class AddPaperNoteHandler(BaseToolHandler):
    tool_name = "add_paper_note"
    input_model = AddPaperNoteInput
    output_model = AddPaperNoteOutputData

    def run(self, payload: AddPaperNoteInput):
        try:
            idem = payload.context.request_id or f"note:{payload.context.user_id}:{payload.paper_id}:{hash(payload.note)}"
            response = get_java_client().add_paper_note(
                AddPaperNoteRequest(
                    user_id=payload.context.user_id,
                    paper_id=payload.paper_id,
                    note=payload.note,
                    idempotency_key=idem,
                )
            )
            return success_result(tool_name=self.tool_name, data=AddPaperNoteOutputData(added=response.added))
        except JavaClientError as exc:
            return failed_result(
                tool_name=self.tool_name,
                error=make_tool_error(
                    code="PROVIDER_FAILURE",
                    message="Real provider failed",
                    error_layer=exc.error_layer,
                    detail={"status_code": exc.status_code},
                    retryable=exc.__class__.__name__.endswith("RetryableError"),
                ),
            )
        except ProviderFailureError as exc:
            return failed_result(tool_name=self.tool_name, error=exc.tool_error)
        except Exception as exc:  # pragma: no cover
            return failed_result(tool_name=self.tool_name, error=wrap_exception(self.tool_name, exc))


add_paper_note_tool = AddPaperNoteHandler()
