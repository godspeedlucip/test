from pydantic import BaseModel

from domain.context import RequestContext
from domain.observability import ObservabilityEvent
from observability.recorder import get_recorder
from tools.base import BaseToolHandler, success_result


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
        get_recorder().record(payload.event)
        return success_result(tool_name=self.tool_name, data=RecordObservabilityEventOutputData(recorded=True))


record_observability_event_tool = RecordObservabilityEventHandler()
