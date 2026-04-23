from pydantic import BaseModel

from domain.context import RequestContext
from integrations import get_java_client
from tools.base import BaseToolHandler, success_result


class SavePaperToLibraryInput(BaseModel):
    context: RequestContext
    paper_id: str


class SavePaperToLibraryOutputData(BaseModel):
    saved: bool


class SavePaperToLibraryHandler(BaseToolHandler):
    tool_name = "save_paper_to_library"
    input_model = SavePaperToLibraryInput
    output_model = SavePaperToLibraryOutputData

    def run(self, payload: SavePaperToLibraryInput):
        get_java_client().save_paper(payload.context.user_id, payload.paper_id)
        return success_result(tool_name=self.tool_name, data=SavePaperToLibraryOutputData(saved=True))


save_paper_to_library_tool = SavePaperToLibraryHandler()
