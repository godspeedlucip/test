from pydantic import BaseModel

from domain.context import RequestContext
from integrations import get_repo
from tools.base import BaseToolHandler, success_result


class AddPaperNoteInput(BaseModel):
    context: RequestContext
    paper_id: str
    note: str


class AddPaperNoteOutputData(BaseModel):
    added: bool


class AddPaperNoteHandler(BaseToolHandler):
    tool_name = "add_paper_note"
    input_model = AddPaperNoteInput
    output_model = AddPaperNoteOutputData

    def run(self, payload: AddPaperNoteInput):
        repo = get_repo()
        repo.notes.setdefault(payload.paper_id, []).append(payload.note)
        return success_result(tool_name=self.tool_name, data=AddPaperNoteOutputData(added=True))


add_paper_note_tool = AddPaperNoteHandler()
