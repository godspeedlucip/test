from pydantic import BaseModel, Field

from domain.context import RequestContext
from integrations import get_java_client
from integrations.java_client import JavaClientError, TagPaperRequest
from integrations.provider_errors import ProviderFailureError
from tools.base import BaseToolHandler, failed_result, make_tool_error, success_result, wrap_exception


class TagPaperInput(BaseModel):
    context: RequestContext
    paper_id: str
    tags: list[str] = Field(default_factory=list)


class TagPaperOutputData(BaseModel):
    tagged: bool
    tags: list[str] = Field(default_factory=list)


class TagPaperHandler(BaseToolHandler):
    tool_name = "tag_paper"
    input_model = TagPaperInput
    output_model = TagPaperOutputData

    def run(self, payload: TagPaperInput):
        try:
            normalized_tags = [t.strip() for t in payload.tags if t and t.strip()]
            idem = (
                f"{payload.context.request_id or 'no-request'}:"
                f"{payload.context.user_id}:{payload.paper_id}:{','.join(sorted(normalized_tags))}"
            )
            response = get_java_client().tag_paper(
                TagPaperRequest(
                    user_id=payload.context.user_id,
                    paper_id=payload.paper_id,
                    tags=normalized_tags,
                    idempotency_key=idem,
                )
            )
            return success_result(tool_name=self.tool_name, data=TagPaperOutputData(tagged=response.tagged, tags=response.tags))
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


tag_paper_tool = TagPaperHandler()
