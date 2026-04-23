from pydantic import BaseModel, Field

from domain.citation import CitationItem
from domain.context import RequestContext
from domain.evidence import EvidenceSpan
from domain.runtime import ModelConfig, PromptConfig, RuntimeConfig
from tools.base import BaseToolHandler, success_result


class GenerateRelatedWorkInput(BaseModel):
    context: RequestContext
    model: ModelConfig | None = None
    prompt: PromptConfig | None = None
    runtime: RuntimeConfig | None = None
    paper_ids: list[str]
    topic: str


class GenerateRelatedWorkOutputData(BaseModel):
    related_work_text: str
    citations: list[CitationItem] = Field(default_factory=list)
    evidence_map: dict[str, list[EvidenceSpan]] = Field(default_factory=dict)


class GenerateRelatedWorkHandler(BaseToolHandler):
    tool_name = "generate_related_work"
    input_model = GenerateRelatedWorkInput
    output_model = GenerateRelatedWorkOutputData

    def run(self, payload: GenerateRelatedWorkInput):
        return success_result(tool_name=self.tool_name, data=GenerateRelatedWorkOutputData(related_work_text=f"Related work on {payload.topic}"))


generate_related_work_tool = GenerateRelatedWorkHandler()
