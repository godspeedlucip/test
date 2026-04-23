from typing import Literal

from pydantic import BaseModel, Field

from domain.context import RequestContext
from domain.evidence import EvidenceSpan, GroundedClaim, InferredClaim
from domain.runtime import ModelConfig, PromptConfig, RuntimeConfig
from integrations import get_llm_client
from tools.base import BaseToolHandler, success_result
from tools.document.retrieve_evidence import RetrieveEvidenceInput, retrieve_evidence_tool


class AskPaperInput(BaseModel):
    context: RequestContext
    model: ModelConfig | None = None
    prompt: PromptConfig | None = None
    runtime: RuntimeConfig | None = None
    document_id: str
    question: str
    answer_style: Literal["concise", "standard", "detailed"] = "standard"
    max_evidences: int = 5
    require_grounding: bool = True


class AskPaperOutputData(BaseModel):
    document_id: str
    answer: str
    evidences: list[EvidenceSpan]
    grounded_claims: list[GroundedClaim] = Field(default_factory=list)
    inferred_claims: list[InferredClaim] = Field(default_factory=list)


class AskPaperHandler(BaseToolHandler):
    tool_name = "ask_paper"
    input_model = AskPaperInput
    output_model = AskPaperOutputData

    def run(self, payload: AskPaperInput):
        evidence_result = retrieve_evidence_tool.execute(
            RetrieveEvidenceInput(
                context=payload.context,
                runtime=payload.runtime,
                document_id=payload.document_id,
                query=payload.question,
                top_k=payload.max_evidences,
            )
        )
        evidences = [EvidenceSpan.model_validate(x) for x in (evidence_result.data or {}).get("evidences", [])]
        evidence_text = "\n".join(f"- {e.text}" for e in evidences)
        answer = get_llm_client().answer(f"Question: {payload.question}\nEvidence:\n{evidence_text}").text
        grounded_claims = []
        if payload.require_grounding and evidences:
            grounded_claims.append(GroundedClaim(claim=answer[:80], evidences=evidences[:2]))
        output = AskPaperOutputData(
            document_id=payload.document_id,
            answer=answer,
            evidences=evidences,
            grounded_claims=grounded_claims,
            inferred_claims=[] if payload.require_grounding else [InferredClaim(claim=answer[:80], based_on_evidences=evidences)],
        )
        return success_result(tool_name=self.tool_name, data=output)


ask_paper_tool = AskPaperHandler()
