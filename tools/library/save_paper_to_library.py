from pydantic import BaseModel

from domain.context import RequestContext
from integrations import get_java_client
from integrations.java_client import JavaClientError, SavePaperToLibraryRequest
from tools.base import BaseToolHandler, failed_result, make_tool_error, success_result, wrap_exception


class SavePaperToLibraryInput(BaseModel):
    context: RequestContext
    paper_id: str


class SavePaperToLibraryOutputData(BaseModel):
    saved: bool


class SavePaperToLibraryHandler(BaseToolHandler):
    tool_name = "save_paper_to_library"
    input_model = SavePaperToLibraryInput
    output_model = SavePaperToLibraryOutputData

    def run(self, payload: SavePaperToLibraryInput):
        try:
            response = get_java_client().save_paper_to_library(
                SavePaperToLibraryRequest(
                    user_id=payload.context.user_id,
                    paper_id=payload.paper_id,
                    idempotency_key=payload.context.request_id,
                )
            )
            return success_result(tool_name=self.tool_name, data=SavePaperToLibraryOutputData(saved=response.saved))
        except JavaClientError as exc:
            return failed_result(
                tool_name=self.tool_name,
                error=make_tool_error(
                    code="java_client_error",
                    message=str(exc),
                    error_layer=exc.error_layer,
                    detail={"status_code": exc.status_code},
                    retryable=exc.__class__.__name__.endswith("RetryableError"),
                ),
            )
        except Exception as exc:  # pragma: no cover
            return failed_result(tool_name=self.tool_name, error=wrap_exception(self.tool_name, exc))


save_paper_to_library_tool = SavePaperToLibraryHandler()
