from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any

from evals.schemas import EvalRunInput, EvalRunOutputData, EvalSampleResult
from domain.runtime import ModelConfig, PromptConfig
from tools.registry import TOOL_REGISTRY


def _dataset_path(dataset_name: str, dataset_version: str) -> Path:
    return Path(__file__).resolve().parents[1] / "datasets" / "tools" / f"{dataset_name}.{dataset_version}.json"


def _assert_result(result_data: dict[str, Any] | None, assertion: dict[str, Any] | None) -> tuple[bool, str]:
    if assertion is None:
        return True, "no assertion"
    if result_data is None:
        return False, "missing result data"
    field = assertion.get("field")
    op = assertion.get("op")
    expected = assertion.get("value")
    actual = result_data.get(field)
    if op == "exists":
        return (actual is not None, f"{field} exists={actual is not None}")
    if op == "gte":
        return (actual is not None and actual >= expected, f"{field}={actual} >= {expected}")
    if op == "contains":
        return (isinstance(actual, str) and str(expected) in actual, f"{field} contains {expected}")
    return False, f"unsupported assertion op: {op}"


def run_tool_eval(
    eval_input: EvalRunInput | None = None,
    model_variants: list[dict[str, Any]] | None = None,
    prompt_variants: list[dict[str, Any]] | None = None,
) -> EvalRunOutputData:
    if eval_input is None:
        eval_input = EvalRunInput.model_validate(
            {
                "context": {"user_id": "eval-user", "request_id": f"eval-tool-{uuid.uuid4()}"},
                "dataset_name": "search_papers_basic",
                "dataset_version": "v1",
                "target_tool": "search_papers",
                "model": {"provider": "mock", "model_name": "mock-llm-v1"},
                "prompt": {"prompt_name": "ask_paper", "prompt_version": "v1"},
            }
        )

    dataset_file = _dataset_path(eval_input.dataset_name, eval_input.dataset_version)
    samples = json.loads(dataset_file.read_text(encoding="utf-8"))
    if eval_input.max_samples is not None:
        samples = samples[: eval_input.max_samples]
    total = len(samples)

    tool = TOOL_REGISTRY[eval_input.target_tool]
    results: list[EvalSampleResult] = []
    for sample in samples:
        started = int(time.time() * 1000)
        payload = dict(sample.get("input", {}))
        payload["context"] = eval_input.context.model_dump()
        payload.setdefault("runtime", eval_input.runtime.model_dump() if eval_input.runtime else None)
        if "model" in tool.input_model.model_fields:
            payload.setdefault("model", eval_input.model.model_dump())
        if "prompt" in tool.input_model.model_fields:
            payload.setdefault("prompt", eval_input.prompt.model_dump())

        tool_result = tool.execute(payload)
        passed, message = _assert_result(tool_result.data, sample.get("assert"))
        if not tool_result.success:
            passed = False
            message = tool_result.error.message if tool_result.error else "tool execution failed"
        latency = int(time.time() * 1000) - started
        results.append(
            EvalSampleResult(
                sample_id=sample["sample_id"],
                passed=passed,
                score=1.0 if passed else 0.0,
                message=message,
                latency_ms=latency,
            )
        )

    completed = len(results)
    pass_count = sum(1 for r in results if r.passed)
    pass_rate = pass_count / max(1, total)
    avg_latency = sum((r.latency_ms or 0) for r in results) / max(1, completed)
    compare_rows: list[dict[str, Any]] = []
    resolved_model_variants = [eval_input.model.model_dump()] if not model_variants else [
        ModelConfig.model_validate(x).model_dump() for x in model_variants
    ]
    resolved_prompt_variants = [eval_input.prompt.model_dump()] if not prompt_variants else [
        PromptConfig.model_validate(x).model_dump() for x in prompt_variants
    ]
    matrix = eval_input.runtime.model_dump().get("eval_compare_matrix") if eval_input.runtime else None
    if isinstance(matrix, dict):
        mv = matrix.get("models")
        pv = matrix.get("prompts")
        if isinstance(mv, list) and mv:
            resolved_model_variants = [ModelConfig.model_validate(x).model_dump() for x in mv]
        if isinstance(pv, list) and pv:
            resolved_prompt_variants = [PromptConfig.model_validate(x).model_dump() for x in pv]
    compare_sample_results: list[EvalSampleResult] = []
    if len(resolved_model_variants) * len(resolved_prompt_variants) > 1:
        for model_item in resolved_model_variants:
            for prompt_item in resolved_prompt_variants:
                local_pass = 0
                for sample in samples:
                    payload = dict(sample.get("input", {}))
                    payload["context"] = eval_input.context.model_dump()
                    payload.setdefault("runtime", eval_input.runtime.model_dump() if eval_input.runtime else None)
                    if "model" in tool.input_model.model_fields:
                        payload["model"] = model_item
                    if "prompt" in tool.input_model.model_fields:
                        payload["prompt"] = prompt_item
                    out = tool.execute(payload)
                    passed_variant, _ = _assert_result(out.data, sample.get("assert"))
                    if out.success and passed_variant:
                        local_pass += 1
                local_pass_rate = round(local_pass / max(1, total), 4)
                compare_rows.append(
                    {"model_name": model_item.get("model_name"), "prompt_name": prompt_item.get("prompt_name"), "prompt_version": prompt_item.get("prompt_version"), "pass_rate": local_pass_rate}
                )
                compare_sample_results.append(
                    EvalSampleResult(
                        sample_id=f"compare::{model_item.get('model_name')}::{prompt_item.get('prompt_name')}::{prompt_item.get('prompt_version')}",
                        passed=local_pass_rate >= 0.5,
                        score=local_pass_rate,
                        message=f"compare_pass_rate={local_pass_rate}",
                        latency_ms=None,
                    )
                )
    return EvalRunOutputData(
        run_id=f"tool-eval-{uuid.uuid4()}",
        total_samples=total,
        completed_samples=completed,
        metrics={
            "pass_rate": round(pass_rate, 4),
            "avg_latency_ms": round(avg_latency, 2),
            "compare_rows_count": float(len(compare_rows)),
        },
        sample_results=results + compare_sample_results,
    )
