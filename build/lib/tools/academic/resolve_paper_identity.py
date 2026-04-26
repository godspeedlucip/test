from pydantic import BaseModel

from domain.context import RequestContext
from domain.paper import PaperMetadata
from integrations import get_arxiv_client
from tools.base import BaseToolHandler, success_result


class ResolvePaperIdentityInput(BaseModel):
    context: RequestContext
    query: str


class ResolvePaperIdentityOutputData(BaseModel):
    paper: PaperMetadata


class ResolvePaperIdentityHandler(BaseToolHandler):
    tool_name = "resolve_paper_identity"
    input_model = ResolvePaperIdentityInput
    output_model = ResolvePaperIdentityOutputData

    def run(self, payload: ResolvePaperIdentityInput):
        paper = get_arxiv_client().resolve(payload.query)
        return success_result(tool_name=self.tool_name, data=ResolvePaperIdentityOutputData(paper=paper))


resolve_paper_identity_tool = ResolvePaperIdentityHandler()
