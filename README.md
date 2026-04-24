# research_agent

Incremental executable research agent built with Python + Pydantic + LangGraph.

## Supported workflows

- QA workflow: `intent_router -> (compute_node | prepare_documents) -> ask_node -> judge_node -> compose_node -> observability_node`
- Compare/export workflow: `intent_router -> (compute_node | prepare_documents) -> compare_node -> judge_node -> export_node -> compose_node -> observability_node`
- Related-work workflow: `intent_router -> (compute_node | prepare_documents) -> related_work_node -> judge/revise/human_review/trajectory_judge -> compose_node -> observability_node`
- Library save workflow (existing): search/select/save/compose/observability
- Compute workflow: `compute_node -> compose_node -> observability_node` (supports python code / table analysis / plot / notebook execution)

## Provider mode switch (mock/real/hybrid)

Use environment variables (see `.env.example`):

- `LLM_PROVIDER_MODE`
- `TRACE_STORE_PROVIDER`
- `OBJECT_STORE_PROVIDER`
- `VECTOR_STORE_PROVIDER`
- `JAVA_CLIENT_MODE`
- `ACADEMIC_PROVIDER_MODE`

Current status:

- `mock`: fully runnable in this repository.
- `real`: interface and config entry exist; some real transports are intentionally not fully wired.
- `hybrid`: tries real path then falls back to mock for minimal continuity.

## Judge pipeline (LLM-as-Judge)

`judge_answer_quality` and `judge_agent_trajectory` now support:

1. prompt loading from `prompts/` via prompt registry
2. LLM runtime invocation
3. strict JSON output parsing + schema validation
4. parse/runtime failure fallback to rule judge
5. explicit fallback marks (`judge_mode=rule-fallback`, `fallback_reason`)
6. `judge_finished` observability events

## Observability query loop

`TraceStore` now supports:

- `get_trace(trace_id)`
- `list_trace_events(trace_id)`
- `aggregate_metrics(start_ms=None, end_ms=None)`

Included implementations:

- `InMemoryTraceStore`
- `FileTraceStore`
- `HybridTraceStore`

`emitter`, `recorder`, and `record_observability_event` tool now share the same trace sink.

## Compute workflow entry

Compute is no longer isolated tools only.

Trigger paths:

- query includes compute intent (`analyze table`, `plot`, `run code`, etc.)
- explicit `table_uri`
- explicit `analysis_code`

`compute_node` can call:

- `execute_python_code`
- `analyze_table`
- `generate_plot`
- `execute_notebook_template`

Artifacts are appended to `state.artifacts`, and file artifacts are reported through Java client contract (`record_file_artifact`).

## LLM runtime governance

- All generation/judge tasks should go through `prompt_registry + model_router + llm_runtime`.
- Runtime records:
1. `model_name`
2. `prompt_version`
3. `token_usage`
4. `estimated_cost` (also stored as `token_usage.estimated_cost_microusd`)

## Eval runner compare mode

- Tool eval compare: run `run_tool_eval(..., model_variants=[...], prompt_variants=[...])`
- Workflow eval compare: run `run_workflow_eval(..., model_variants=[...], prompt_variants=[...])`
- Compare outputs are exposed as `sample_results` entries with `sample_id` starting `compare::`.

## Java platform collaboration loop

Workflow lifecycle now updates task status through Java client:

- request started
- running updates during node execution
- succeeded/partial/failed at finish

Artifact-producing nodes (`compute_node`, `export_node`) record file artifacts with idempotency keys.

## Checkpoint / human review minimal recovery loop

- checkpoint store supports save + load by `checkpoint_id`
- `graph/recovery.py` provides:
  - `load_checkpoint(checkpoint_id)`
  - `resume_from_checkpoint(checkpoint_id, workflow_runner)`
  - `apply_human_review_decision(state, decision, note=None)`
- human review node accepts decision backflow and routes to `trajectory_judge` or `revise`

## Run

```bash
pip install -e .[dev]
pytest
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Phase 3 local acceptance quick checks

```bash
python -m pytest -q tests/unit/test_compute_tools.py tests/integration/test_compute_workflow_integration.py
python -m pytest -q tests/unit/test_llmops_governance.py
```
