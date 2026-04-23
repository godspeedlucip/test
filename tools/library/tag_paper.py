from pydantic import BaseModel, Field

from domain.context import RequestContext
from tools.base import BaseToolHandler, success_result


class TagPaperInput(BaseModel):
    context: RequestContext
    paper_id: str
    tags: list[str] = Field(default_factory=list)


class TagPaperOutputData(BaseModel):
    tagged: bool


class TagPaperHandler(BaseToolHandler):
    tool_name = "tag_paper"
    input_model = TagPaperInput
    output_model = TagPaperOutputData

    def run(self, payload: TagPaperInput):
        return success_result(tool_name=self.tool_name, data=TagPaperOutputData(tagged=True))


tag_paper_tool = TagPaperHandler()
