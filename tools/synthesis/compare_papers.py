from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, Field

from domain.base import ToolMeta
from domain.context import RequestContext
from domain.evidence import EvidenceSpan
from domain.runtime import ModelConfig, PromptConfig, RuntimeConfig
from integrations import get_repo, resolve_prompt_config, run_llm_task
from tools.base import BaseToolHandler, failed_result, make_tool_error, success_result


class ComparisonRow(BaseModel):
    paper_id: str
    title: str
    values: dict[str, Any]
    evidence_map: dict[str, list[EvidenceSpan]] = Field(default_factory=dict)


class ComparePapersInput(BaseModel):
    context: RequestContext
    model: ModelConfig | None = None
    prompt: PromptConfig | None = None
    runtime: RuntimeConfig | None = None
    paper_ids: list[str]
    document_ids: list[str]
    dimensions: list[str] = Field(default_factory=lambda: ["method", "dataset", "metrics", "limitations"])
    output_format: Literal["paragraph", "table", "both"] = "both"
    require_evidence: bool = True
    facts_by_paper: dict[str, dict[str, Any]] = Field(default_factory=dict)


class ComparePapersOutputData(BaseModel):
    summary: str
    table: list[ComparisonRow] = Field(default_factory=list)
    key_differences: list[str] = Field(default_factory=list)
    common_patterns: list[str] = Field(default_factory=list)


class ComparePapersHandler(BaseToolHandler):
    tool_name = "compare_papers"
    input_model = ComparePapersInput
    output_model = ComparePapersOutputData

    def run(self, payload: ComparePapersInput):
        if not payload.paper_ids:
            return failed_result(
                tool_name=self.tool_name,
                error=make_tool_error(code="invalid_input", message="paper_ids is required"),
            )
        repo = get_repo()
        prompt_cfg = resolve_prompt_config(payload.prompt, default_name="compare_papers")
        rows: list[ComparisonRow] = []

        for paper_id in payload.paper_ids:
            paper = repo.papers.get(paper_id)
            title = paper.title if paper else paper_id
            fact = payload.facts_by_paper.get(paper_id, {})
            values: dict[str, Any] = {}
            evidence_map: dict[str, list[EvidenceSpan]] = {}
            fact_evidence = [EvidenceSpan.model_validate(e) for e in fact.get("evidence_map", [])]
            for dim in payload.dimensions:
                raw = fact.get(dim)
                if raw is None and dim == "dataset":
                    raw = fact.get("dataset", [])
                if raw is None and dim == "metrics":
                    raw = fact.get("metrics", {})
                values[dim] = raw if raw not in (None, "", [], {}) else "not_available"
                if fact_evidence and payload.require_evidence:
                    evidence_map[dim] = fact_evidence[:2]
            rows.append(ComparisonRow(paper_id=paper_id, title=title, values=values, evidence_map=evidence_map))

        if payload.require_evidence and not any(row.evidence_map for row in rows):
            return failed_result(
                tool_name=self.tool_name,
                error=make_tool_error(code="insufficient_evidence", message="compare_papers requires evidence-backed facts"),
            )

        method_set = {str(r.values.get("method")) for r in rows if r.values.get("method") not in (None, "not_available")}
        dataset_set = {str(x) for r in rows for x in (r.values.get("dataset") if isinstance(r.values.get("dataset"), list) else [])}
        key_differences = []
        if len(method_set) > 1:
            key_differences.append("Methods vary across papers")
        if len(dataset_set) > 1:
            key_differences.append("Datasets differ across studies")
        if not key_differences:
            key_differences.append("Most papers share similar reported structure")

        common_patterns = []
        if method_set:
            common_patterns.append(f"Method focus count={len(method_set)}")
        if dataset_set:
            common_patterns.append(f"Dataset mentions count={len(dataset_set)}")
        if not common_patterns:
            common_patterns.append("Evidence density is low across available chunks")

        llm_result = run_llm_task(
            task_type="compare_papers",
            prompt_name=prompt_cfg.prompt_name,
            prompt_version=prompt_cfg.prompt_version,
            body=(
                f"Dimensions: {', '.join(payload.dimensions)}\n"
                f"Output format: {payload.output_format}\n"
                f"Facts by paper:\n{json.dumps(payload.facts_by_paper, ensure_ascii=False)}"
            ),
            requested_model=payload.model,
        )
        output = ComparePapersOutputData(
            summary=llm_result.response.text,
            table=rows,
            key_differences=key_differences,
            common_patterns=common_patterns,
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


compare_papers_tool = ComparePapersHandler()
