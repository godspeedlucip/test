from pydantic import BaseModel, Field

from domain.context import RequestContext
from integrations import get_repo
from tools.base import BaseToolHandler, success_result


class ListLibraryPapersInput(BaseModel):
    context: RequestContext


class ListLibraryPapersOutputData(BaseModel):
    paper_ids: list[str] = Field(default_factory=list)


class ListLibraryPapersHandler(BaseToolHandler):
    tool_name = "list_library_papers"
    input_model = ListLibraryPapersInput
    output_model = ListLibraryPapersOutputData

    def run(self, payload: ListLibraryPapersInput):
        ids = get_repo().library.get(payload.context.user_id, [])
        return success_result(tool_name=self.tool_name, data=ListLibraryPapersOutputData(paper_ids=ids))


list_library_papers_tool = ListLibraryPapersHandler()
