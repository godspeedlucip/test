from pydantic import BaseModel

from domain.context import RequestContext
from tools.base import BaseToolHandler, success_result


class GeneratePlotInput(BaseModel):
    context: RequestContext
    spec: dict


class GeneratePlotOutputData(BaseModel):
    image_uri: str


class GeneratePlotHandler(BaseToolHandler):
    tool_name = "generate_plot"
    input_model = GeneratePlotInput
    output_model = GeneratePlotOutputData

    def run(self, payload: GeneratePlotInput):
        return success_result(tool_name=self.tool_name, data=GeneratePlotOutputData(image_uri="memory://plot/mock.png"))


generate_plot_tool = GeneratePlotHandler()
