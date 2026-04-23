from pydantic import BaseModel, Field

from domain.context import RequestContext
from tools.base import BaseToolHandler, success_result


class FormatReferencesInput(BaseModel):
    context: RequestContext
    references: list[str] = Field(default_factory=list)


class FormatReferencesOutputData(BaseModel):
    formatted: list[str] = Field(default_factory=list)


class FormatReferencesHandler(BaseToolHandler):
    tool_name = "format_references"
    input_model = FormatReferencesInput
    output_model = FormatReferencesOutputData

    def run(self, payload: FormatReferencesInput):
        return success_result(tool_name=self.tool_name, data=FormatReferencesOutputData(formatted=payload.references))


format_references_tool = FormatReferencesHandler()
