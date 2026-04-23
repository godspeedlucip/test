from pydantic import BaseModel, Field

from domain.context import RequestContext
from integrations import get_java_client
from integrations.java_client import JavaClientError, ListLibraryPapersRequest
from tools.base import BaseToolHandler, failed_result, make_tool_error, success_result, wrap_exception


class ListLibraryPapersInput(BaseModel):
    context: RequestContext


class ListLibraryPapersOutputData(BaseModel):
    paper_ids: list[str] = Field(default_factory=list)


class ListLibraryPapersHandler(BaseToolHandler):
    tool_name = "list_library_papers"
    input_model = ListLibraryPapersInput
    output_model = ListLibraryPapersOutputData

    def run(self, payload: ListLibraryPapersInput):
        try:
            response = get_java_client().list_library_papers(ListLibraryPapersRequest(user_id=payload.context.user_id))
            return success_result(tool_name=self.tool_name, data=ListLibraryPapersOutputData(paper_ids=response.paper_ids))
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


list_library_papers_tool = ListLibraryPapersHandler()
