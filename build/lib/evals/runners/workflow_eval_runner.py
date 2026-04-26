from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any

from domain.runtime import ModelConfig, PromptConfig
from evals.schemas import EvalRunOutputData, EvalSampleResult
from graph.workflows.compare_export_workflow import build_compare_export_workflow
from graph.workflows.compute_workflow import build_compute_workflow
from graph.workflows.qa_workflow import build_qa_workflow
from graph.workflows.related_work_workflow import build_related_work_workflow
from tools.academic.search_papers import SearchPapersInput, search_papers_tool


def _dataset_path(dataset_name: str, dataset_version: str) -> Path:
    return Path(__file__).resolve().parents[1] / "datasets" / "workflows" / f"{dataset_name}.{dataset_version}.json"


def _workflow_by_name(name: str):
    if name == "qa_workflow":
        return build_qa_workflow()
    if name == "compare_export_workflow":
        return build_compare_export_workflow()
    if name == "related_work_workflow":
        return build_related_work_workflow()
    if name == "compute_workflow":
        return build_compute_workflow()
    raise ValueError(f"unknown workflow: {name}")


def _prepare_input(sample_input: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    payload = dict(sample_input)
    payload["context"] = context
    if "paper_ids" not in payload and sample_input.get("search_query"):
        sr = search_papers_tool.execute(
            SearchPapersInput(
                context=context,
                query=sample_input["search_query"],
                top_k=sample_input.get("top_k", 2),
            )
        )
        payload["paper_ids"] = [x["paper_id"] for x in (sr.data or {}).get("papers", [])[: sample_input.get("top_k", 2)]]
    return payload


def run_workflow_eval(
    dataset_name: str = "workflow_smoke",
    dataset_version: str = "v1",
    model_variants: list[dict[str, Any]] | None = None,
    prompt_variants: list[dict[str, Any]] | None = None,
) -> EvalRunOutputData:
    dataset_file = _dataset_path(dataset_name, dataset_version)
    samples = json.loads(dataset_file.read_text(encoding="utf-8"))

    sample_results: list[EvalSampleResult] = []
    for sample in samples:
        started = int(time.time() * 1000)
        wf = _workflow_by_name(sample["workflow"])
        context = {"user_id": "eval-user", "request_id": f"eval-wf-{uuid.uuid4()}"}
        payload = _prepare_input(sample.get("input", {}), context)
        out = wf.invoke(payload)
        expected_key = sample.get("expect", {}).get("key", "final_answer")
        actual = out.get(expected_key)
        passed = actual is not None and (not isinstance(actual, str) or len(actual.strip()) > 0)
        message = f"{expected_key} present={passed}"
        sample_results.append(
            EvalSampleResult(
                sample_id=sample["sample_id"],
                passed=passed,
                score=1.0 if passed else 0.0,
                message=message,
                latency_ms=int(time.time() * 1000) - started,
            )
        )

    total = len(sample_results)
    completed = total
    pass_rate = sum(1 for r in sample_results if r.passed) / max(1, total)
    avg_latency = sum((r.latency_ms or 0) for r in sample_results) / max(1, completed)
    compare_results: list[EvalSampleResult] = []
    compare_count = 0
    models = [ModelConfig(provider="mock", model_name="mock-llm-v1").model_dump()] if not model_variants else [
        ModelConfig.model_validate(x).model_dump() for x in model_variants
    ]
    prompts = [PromptConfig(prompt_name="ask_paper", prompt_version="v1").model_dump()] if not prompt_variants else [
        PromptConfig.model_validate(x).model_dump() for x in prompt_variants
    ]
    if len(models) * len(prompts) > 1:
        for m in models:
            for p in prompts:
                local_pass = 0
                for sample in samples:
                    wf = _workflow_by_name(sample["workflow"])
                    context = {"user_id": "eval-user", "request_id": f"eval-wf-{uuid.uuid4()}"}
                    payload = _prepare_input(sample.get("input", {}), context)
                    payload["model"] = m
                    payload["prompt"] = p
                    out = wf.invoke(payload)
                    expected_key = sample.get("expect", {}).get("key", "final_answer")
                    actual = out.get(expected_key)
                    passed = actual is not None and (not isinstance(actual, str) or len(actual.strip()) > 0)
                    if passed:
                        local_pass += 1
                local_rate = round(local_pass / max(1, len(samples)), 4)
                compare_count += 1
                compare_results.append(
                    EvalSampleResult(
                        sample_id=f"compare::{m.get('model_name')}::{p.get('prompt_name')}::{p.get('prompt_version')}",
                        passed=local_rate >= 0.5,
                        score=local_rate,
                        message=f"compare_pass_rate={local_rate}",
                        latency_ms=None,
                    )
                )

    return EvalRunOutputData(
        run_id=f"workflow-eval-{uuid.uuid4()}",
        total_samples=total,
        completed_samples=completed,
        metrics={"pass_rate": round(pass_rate, 4), "avg_latency_ms": round(avg_latency, 2), "compare_rows_count": float(compare_count)},
        sample_results=sample_results + compare_results,
    )
