from pydantic import BaseModel, Field

from domain.context import RequestContext
from domain.evidence import EvidenceSpan
from domain.runtime import ModelConfig, PromptConfig, RuntimeConfig
from tools.base import BaseToolHandler, success_result


class PaperFact(BaseModel):
    paper_id: str
    task: str | None = None
    method: str | None = None
    dataset: list[str] = Field(default_factory=list)
    metrics: dict[str, str] = Field(default_factory=dict)
    baselines: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    evidence_map: list[EvidenceSpan] = Field(default_factory=list)


class ExtractPaperFactsInput(BaseModel):
    context: RequestContext
    model: ModelConfig | None = None
    prompt: PromptConfig | None = None
    runtime: RuntimeConfig | None = None
    document_id: str


class ExtractPaperFactsOutputData(BaseModel):
    facts: PaperFact


class ExtractPaperFactsHandler(BaseToolHandler):
    tool_name = "extract_paper_facts"
    input_model = ExtractPaperFactsInput
    output_model = ExtractPaperFactsOutputData

    def run(self, payload: ExtractPaperFactsInput):
        return success_result(
            tool_name=self.tool_name,
            data=ExtractPaperFactsOutputData(facts=PaperFact(paper_id=payload.document_id, method="mock method")),
        )


extract_paper_facts_tool = ExtractPaperFactsHandler()
