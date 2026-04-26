from __future__ import annotations

from pydantic import BaseModel, Field

from domain.base import ToolMeta
from domain.context import RequestContext
from domain.evidence import EvidenceSpan
from domain.runtime import ModelConfig, PromptConfig, RuntimeConfig
from integrations import get_repo, resolve_prompt_config, run_llm_task
from tools.base import BaseToolHandler, failed_result, make_tool_error, success_result
from tools.document.retrieve_evidence import RetrieveEvidenceInput, retrieve_evidence_tool


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
    dimensions: list[str] = Field(default_factory=lambda: ["task", "method", "dataset", "metrics", "limitations"])


class ExtractPaperFactsOutputData(BaseModel):
    facts: PaperFact


class ExtractPaperFactsHandler(BaseToolHandler):
    tool_name = "extract_paper_facts"
    input_model = ExtractPaperFactsInput
    output_model = ExtractPaperFactsOutputData

    def run(self, payload: ExtractPaperFactsInput):
        repo = get_repo()
        record = repo.documents.get(payload.document_id)
        if record is None:
            return failed_result(
                tool_name=self.tool_name,
                error=make_tool_error(code="document_not_found", message=f"document {payload.document_id} not found"),
            )

        prompt_cfg = resolve_prompt_config(payload.prompt, default_name="compare_papers")
        paper = repo.papers.get(record.paper_id or "")
        paper_id = record.paper_id or payload.document_id
        title = paper.title if paper else paper_id

        evidence_spans: list[EvidenceSpan] = []
        for dim in payload.dimensions:
            retrieval = retrieve_evidence_tool.execute(
                RetrieveEvidenceInput(
                    context=payload.context,
                    runtime=payload.runtime,
                    document_id=payload.document_id,
                    query=f"{dim} of {title}",
                    top_k=2,
                )
            )
            if retrieval.success:
                evidence_spans.extend(EvidenceSpan.model_validate(x) for x in retrieval.data.get("evidences", []))
        unique_evidences = list({ev.anchor.chunk_id or f"ev-{idx}": ev for idx, ev in enumerate(evidence_spans)}.values())
        if not unique_evidences:
            return failed_result(
                tool_name=self.tool_name,
                error=make_tool_error(code="insufficient_evidence", message=f"no evidence found for {payload.document_id}"),
            )

        evidence_text = "\n".join(f"- [{e.anchor.section_title or 'section'}] {e.text}" for e in unique_evidences[:8])
        llm_result = run_llm_task(
            task_type="extract_paper_facts",
            prompt_name=prompt_cfg.prompt_name,
            prompt_version=prompt_cfg.prompt_version,
            body=(
                f"Document: {payload.document_id}\n"
                f"Paper: {title}\n"
                f"Dimensions: {', '.join(payload.dimensions)}\n"
                f"Evidence:\n{evidence_text}\n"
                "Return concise fact synthesis."
            ),
            requested_model=payload.model,
        )
        llm_text = llm_result.response.text.strip()
        fact = PaperFact(
            paper_id=paper_id,
            task=llm_text[:220] if "task" in payload.dimensions else None,
            method=llm_text[:220] if "method" in payload.dimensions else None,
            dataset=[e.anchor.section_title or "dataset_not_specified" for e in unique_evidences[:2]]
            if "dataset" in payload.dimensions
            else [],
            metrics={"summary": llm_text[:220]} if "metrics" in payload.dimensions else {},
            baselines=[f"baseline_from_{paper_id}"] if "metrics" in payload.dimensions else [],
            strengths=[f"Grounded on {len(unique_evidences)} evidence spans"],
            limitations=["Synthesis quality depends on extracted evidence coverage"],
            evidence_map=unique_evidences,
        )
        meta = ToolMeta(
            tool_name=self.tool_name,
            model_name=llm_result.response.model_name,
            prompt_name=llm_result.loaded_prompt.prompt_name,
            prompt_version=llm_result.loaded_prompt.prompt_version,
            token_usage=llm_result.response.token_usage,
            latency_ms=llm_result.latency_ms,
        )
        return success_result(tool_name=self.tool_name, data=ExtractPaperFactsOutputData(facts=fact), meta=meta)


extract_paper_facts_tool = ExtractPaperFactsHandler()
