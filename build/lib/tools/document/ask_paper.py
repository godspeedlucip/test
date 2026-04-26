from typing import Literal

from pydantic import BaseModel, Field

from domain.base import ToolMeta
from domain.context import RequestContext
from domain.evidence import EvidenceSpan, GroundedClaim, InferredClaim
from domain.runtime import ModelConfig, PromptConfig, RuntimeConfig
from integrations import resolve_prompt_config, run_llm_task
from tools.base import BaseToolHandler, failed_result, make_tool_error, success_result
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
        prompt_cfg = resolve_prompt_config(payload.prompt, default_name="ask_paper")
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
        if payload.require_grounding and not evidences:
            return failed_result(
                tool_name=self.tool_name,
                error=make_tool_error(code="insufficient_evidence", message=f"no evidence found for {payload.document_id}"),
            )
        evidence_text = "\n".join(f"- {e.text}" for e in evidences)
        llm_result = run_llm_task(
            task_type="ask_paper",
            prompt_name=prompt_cfg.prompt_name,
            prompt_version=prompt_cfg.prompt_version,
            body=f"Question: {payload.question}\nAnswer Style: {payload.answer_style}\nEvidence:\n{evidence_text}",
            requested_model=payload.model,
        )
        answer = llm_result.response.text
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
        meta = ToolMeta(
            tool_name=self.tool_name,
            model_name=llm_result.response.model_name,
            prompt_name=llm_result.loaded_prompt.prompt_name,
            prompt_version=llm_result.loaded_prompt.prompt_version,
            token_usage=llm_result.response.token_usage,
            latency_ms=llm_result.latency_ms,
        )
        return success_result(tool_name=self.tool_name, data=output, meta=meta)


ask_paper_tool = AskPaperHandler()
