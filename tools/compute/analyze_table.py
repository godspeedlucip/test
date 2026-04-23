from pydantic import BaseModel

from domain.context import RequestContext
from tools.base import BaseToolHandler, success_result


class AnalyzeTableInput(BaseModel):
    context: RequestContext
    table_uri: str


class AnalyzeTableOutputData(BaseModel):
    summary: str


class AnalyzeTableHandler(BaseToolHandler):
    tool_name = "analyze_table"
    input_model = AnalyzeTableInput
    output_model = AnalyzeTableOutputData

    def run(self, payload: AnalyzeTableInput):
        return success_result(tool_name=self.tool_name, data=AnalyzeTableOutputData(summary="mock table analysis"))


analyze_table_tool = AnalyzeTableHandler()
