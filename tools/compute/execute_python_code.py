from pydantic import BaseModel

from domain.context import RequestContext
from tools.base import BaseToolHandler, success_result


class ExecutePythonCodeInput(BaseModel):
    context: RequestContext
    code: str


class ExecutePythonCodeOutputData(BaseModel):
    stdout: str


class ExecutePythonCodeHandler(BaseToolHandler):
    tool_name = "execute_python_code"
    input_model = ExecutePythonCodeInput
    output_model = ExecutePythonCodeOutputData

    def run(self, payload: ExecutePythonCodeInput):
        return success_result(tool_name=self.tool_name, data=ExecutePythonCodeOutputData(stdout="mock execution"))


execute_python_code_tool = ExecutePythonCodeHandler()
