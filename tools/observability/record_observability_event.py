from pydantic import BaseModel

from domain.context import RequestContext
from domain.observability import ObservabilityEvent
from integrations import get_java_client
from integrations.java_client import JavaClientError, ReportObservabilityEventRequest
from integrations.provider_errors import ProviderFailureError
from observability.recorder import get_recorder
from tools.base import BaseToolHandler, failed_result, make_tool_error, success_result, wrap_exception


class RecordObservabilityEventInput(BaseModel):
    context: RequestContext
    event: ObservabilityEvent


class RecordObservabilityEventOutputData(BaseModel):
    recorded: bool


class RecordObservabilityEventHandler(BaseToolHandler):
    tool_name = "record_observability_event"
    input_model = RecordObservabilityEventInput
    output_model = RecordObservabilityEventOutputData

    def run(self, payload: RecordObservabilityEventInput):
        try:
            # Unified sink with idempotent append on trace/span/event type.
            get_recorder().record(payload.event)
            idem = payload.context.request_id or f"{payload.event.trace_id}:{payload.event.event_type}:{payload.event.span_id}"
            get_java_client().report_observability_event(
                ReportObservabilityEventRequest(
                    trace_id=payload.event.trace_id,
                    event_type=payload.event.event_type,
                    payload=payload.event.payload,
                    idempotency_key=idem,
                )
            )
            return success_result(tool_name=self.tool_name, data=RecordObservabilityEventOutputData(recorded=True))
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


record_observability_event_tool = RecordObservabilityEventHandler()
