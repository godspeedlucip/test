from pydantic import BaseModel, Field

from domain.base import ToolMeta
from domain.citation import CitationItem
from domain.context import RequestContext
from domain.evidence import EvidenceSpan
from domain.runtime import ModelConfig, PromptConfig, RuntimeConfig
from integrations import get_repo, resolve_prompt_config, run_llm_task
from tools.base import BaseToolHandler, success_result


class GenerateRelatedWorkInput(BaseModel):
    context: RequestContext
    model: ModelConfig | None = None
    prompt: PromptConfig | None = None
    runtime: RuntimeConfig | None = None
    paper_ids: list[str]
    topic: str
    target_length: str = "medium"
    require_citations: bool = True
    comparison: dict = Field(default_factory=dict)
    paper_facts: dict[str, dict] = Field(default_factory=dict)


class GenerateRelatedWorkOutputData(BaseModel):
    related_work_text: str
    citations: list[CitationItem] = Field(default_factory=list)
    evidence_map: dict[str, list[EvidenceSpan]] = Field(default_factory=dict)


class GenerateRelatedWorkHandler(BaseToolHandler):
    tool_name = "generate_related_work"
    input_model = GenerateRelatedWorkInput
    output_model = GenerateRelatedWorkOutputData

    def run(self, payload: GenerateRelatedWorkInput):
        prompt_cfg = resolve_prompt_config(payload.prompt, default_name="related_work")
        repo = get_repo()
        comparison_summary = payload.comparison.get("summary", "")
        key_diffs = payload.comparison.get("key_differences", [])
        common_patterns = payload.comparison.get("common_patterns", [])

        fact_snippets = []
        evidence_map: dict[str, list[EvidenceSpan]] = {}
        for pid in payload.paper_ids:
            fact = payload.paper_facts.get(pid, {})
            method = fact.get("method", "method not specified")
            dataset = fact.get("dataset", [])
            dataset_text = ", ".join(dataset) if isinstance(dataset, list) else str(dataset)
            fact_snippets.append(f"{pid}: method={method}; dataset={dataset_text or 'n/a'}")
            evidence_map[pid] = [EvidenceSpan.model_validate(x) for x in fact.get("evidence_map", [])[:2]]

        length_hint = {"short": 80, "medium": 180, "long": 320}.get(payload.target_length, 180)
        body = (
            f"Topic: {payload.topic}\n"
            f"Comparison Summary: {comparison_summary}\n"
            f"Key Differences: {key_diffs}\n"
            f"Common Patterns: {common_patterns}\n"
            f"Facts:\n- " + "\n- ".join(fact_snippets) + "\n\n"
            f"Write a related work paragraph within about {length_hint} words."
        )
        llm_result = run_llm_task(
            task_type="generate_related_work",
            prompt_name=prompt_cfg.prompt_name,
            prompt_version=prompt_cfg.prompt_version,
            body=body,
            requested_model=payload.model,
        )
        related_text = llm_result.response.text

        citations: list[CitationItem] = []
        if payload.require_citations:
            for pid in payload.paper_ids:
                paper = repo.papers.get(pid)
                citations.append(
                    CitationItem(
                        paper_id=pid,
                        title=paper.title if paper else pid,
                        doi=paper.doi if paper else None,
                        citation_text=f"({pid})",
                    )
                )

        meta = ToolMeta(
            tool_name=self.tool_name,
            model_name=llm_result.response.model_name,
            prompt_name=llm_result.loaded_prompt.prompt_name,
            prompt_version=llm_result.loaded_prompt.prompt_version,
            token_usage=llm_result.response.token_usage,
            latency_ms=llm_result.latency_ms,
        )
        return success_result(
            tool_name=self.tool_name,
            data=GenerateRelatedWorkOutputData(
                related_work_text=related_text,
                citations=citations,
                evidence_map=evidence_map,
            ),
            meta=meta,
        )


generate_related_work_tool = GenerateRelatedWorkHandler()
