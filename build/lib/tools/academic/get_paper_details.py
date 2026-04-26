from pydantic import BaseModel

from domain.context import RequestContext
from domain.paper import PaperMetadata
from integrations import get_repo
from tools.base import BaseToolHandler, failed_result, make_tool_error, success_result


class GetPaperDetailsInput(BaseModel):
    context: RequestContext
    paper_id: str


class GetPaperDetailsOutputData(BaseModel):
    paper: PaperMetadata


class GetPaperDetailsHandler(BaseToolHandler):
    tool_name = "get_paper_details"
    input_model = GetPaperDetailsInput
    output_model = GetPaperDetailsOutputData

    def run(self, payload: GetPaperDetailsInput):
        paper = get_repo().papers.get(payload.paper_id)
        if not paper:
            return failed_result(tool_name=self.tool_name, error=make_tool_error(code="paper_not_found", message=payload.paper_id))
        return success_result(tool_name=self.tool_name, data=GetPaperDetailsOutputData(paper=paper))


get_paper_details_tool = GetPaperDetailsHandler()
