from pydantic import BaseModel

from domain.context import RequestContext
from tools.base import BaseToolHandler, success_result


class ExecuteNotebookTemplateInput(BaseModel):
    context: RequestContext
    template_id: str


class ExecuteNotebookTemplateOutputData(BaseModel):
    executed: bool


class ExecuteNotebookTemplateHandler(BaseToolHandler):
    tool_name = "execute_notebook_template"
    input_model = ExecuteNotebookTemplateInput
    output_model = ExecuteNotebookTemplateOutputData

    def run(self, payload: ExecuteNotebookTemplateInput):
        return success_result(tool_name=self.tool_name, data=ExecuteNotebookTemplateOutputData(executed=True))


execute_notebook_template_tool = ExecuteNotebookTemplateHandler()
