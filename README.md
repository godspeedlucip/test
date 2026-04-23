# research_agent

基于 **Python 3.11 + Pydantic v2 + LangGraph** 的可执行科研 Agent（最小可运行版本）。

## 已实现范围

- 完整目录结构（含 Phase 1/2/3 工程占位）
- `domain/` 基础模型
- `tools/base.py`：`BaseToolHandler`、`ToolResult`、错误包装
- `tools/registry.py`：`TOOL_REGISTRY`
- Phase 1 核心工具（独立文件，含 Input/Output/Handler/meta/异常）
  - `search_papers`
  - `fetch_pdf`
  - `parse_pdf`
  - `index_document`
  - `get_document_status`
  - `retrieve_evidence`
  - `ask_paper`
  - `compare_papers`
  - `export_bibtex`
  - `judge_answer_quality`
  - `record_observability_event`
- `graph/` 两条 workflow
  - 单篇论文 QA workflow
  - 多论文 compare + export workflow
- `judge/` 结构化 JSON 评估器
- `observability/` 统一事件记录接口，并在 graph 节点和 tool 调用处埋点
- `tests/`：domain、tools、workflows 核心测试

## 本地运行

1. 创建并激活 Python 3.11 环境
2. 安装依赖

```bash
pip install -e .[dev]
```

3. 运行测试

```bash
pytest
```

4. 跑 demo

```bash
python -m app.main
```

## 如何替换 provider

当前 `integrations/` 下默认是 mock/stub 实现，接口保持稳定。

- 论文检索：替换 `integrations/openalex_client.py`
- DOI 详情：替换 `integrations/crossref_client.py`
- arXiv 解析：替换 `integrations/arxiv_client.py`
- LLM：替换 `integrations/llm_client.py`
- 向量检索：替换 `integrations/vector_store.py`
- 对象存储：替换 `integrations/object_store.py`
- Java 平台集成：替换 `integrations/java_client.py`

建议保持原有 `get_*()` 工厂函数和返回对象方法签名不变，这样 tools/graph 无需改动。

## 设计原则

- graph 节点只做编排，业务逻辑尽量放在 tools / judge / integrations
- Tool 输出统一 `ToolResult`
- 生成与评估解耦（generate -> judge）
- 所有外部调用均可替换 adapter

## LLMOps 治理（最小闭环）

### 1. 如何新增 Prompt

1. 在 `prompts/<prompt_name>/` 下新增版本文件，例如 `prompts/ask_paper/v2.txt`。
2. 保持纯文本模板，`integrations/prompt_registry.py` 会按 `prompt_name + version` 加载。
3. 如果调用侧未显式传版本，默认加载该 prompt 目录下最新版本（按版本名排序）。

### 2. 如何升级版本

1. 新增新版本文件（如 `v2.txt`），不要覆盖旧版本。
2. 在调用入参中把 `PromptConfig.prompt_version` 改为新版本，或依赖默认版本切换。
3. 建议同时运行 `python -m scripts.run_local_eval` 验证回归。

### 3. 如何配置 Model Route

1. 在 `integrations/model_router.py` 的 `InMemoryModelRouter` 中为 `task_type` 配置 `ModelRoutingPolicy`。
2. `primary_model` 是主模型，`fallback_models` 是降级模型链。
3. 执行链路通过 `integrations/llm_runtime.py` 接入路由与 fallback；主模型失败会自动尝试 fallback。

### 4. 如何新增 Eval Case

1. Tool Eval 样例：新增到 `evals/datasets/tools/<dataset_name>.<version>.json`。
2. Workflow Eval 样例：新增到 `evals/datasets/workflows/<dataset_name>.<version>.json`。
3. 每个样例至少包含 `sample_id` 和 `input`，可附加断言（tool）或 expect key（workflow）。
4. 使用 `run_tool_eval` / `run_workflow_eval` 运行并查看结构化 `sample_results` 与聚合 `metrics`。

---

## FastAPI Service (Commit 1)

Run the API server:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Health endpoints:

- `GET /health`
- `GET /observability/health`

Local demo workflow entry is still available:

```bash
python -m app.main
```

## Compute Sandbox Notes

- `execute_python_code` now runs code in a subprocess with timeout control.
- A minimal safety layer blocks dangerous imports/calls (for example `socket`, `subprocess`, `os.system`, `shutil.rmtree`).
- Network access is disabled in the sandbox process.
- Tools return `ToolResult` consistently; invalid input/runtime infrastructure errors are wrapped as `ToolError`.
- Artifacts are stored under `.artifacts/<run_id>/` and returned as both `file://` URI and absolute path.
- `analyze_table` supports `csv`, `tsv`, and `xlsx`.
- `generate_plot` supports `line`, `bar`, `scatter`, and `histogram`.
- `execute_notebook_template` accepts `template_path` or `notebook_json`, injects parameters, executes code cells sequentially, and outputs an executed notebook artifact.

## Java Client Contract (Commit 2)

`integrations/java_client.py` now provides a unified platform contract layer:

- DTOs:
  - `SavePaperToLibraryRequest/Response`
  - `ListLibraryPapersRequest/Response`
  - `AddPaperNoteRequest/Response`
  - `RecordFileArtifactRequest/Response`
  - `UpdateTaskStatusRequest/Response`
  - `ReportObservabilityEventRequest/Response`
- Client capabilities: `base_url`, `timeout`, `Authorization` header, retry for retryable errors only.
- Error model:
  - `JavaClientError`
  - `JavaClientRetryableError`
  - `JavaClientNonRetryableError`
- Side-effect requests support `idempotency_key` and map failures to `ToolError.error_layer` (`network`/`storage`).

Environment variables:

- `JAVA_CLIENT_BASE_URL` (set to enable HTTP Java client; otherwise in-memory mock is used)
- `JAVA_CLIENT_TIMEOUT_SECONDS`
- `JAVA_CLIENT_AUTH_HEADER`
- `JAVA_CLIENT_MAX_RETRIES`
- `JAVA_CLIENT_RETRY_BACKOFF_SECONDS`

## Prompt Registry Governance (Commit 2)

Prompt selection is now registry-driven instead of filename max-version:

- Registry file: `prompts/registry.json`
- Metadata per prompt version includes: `prompt_name`, `version`, `status`, `owner`, `change_log`
- Exactly one `active` version per prompt is required
- Default loading selects active version
- `deprecated` versions are never selected by default
- Explicit version loading is supported (including deprecated)
- Illegal registry config (missing active / duplicate entries / missing prompt file) raises config errors

## Commit 3 Finalization

### Service Startup

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Workflow APIs

- `POST /workflows/qa`
- `POST /workflows/compare`
- `POST /workflows/related-work`
- `POST /workflows/library/save`

Example payload (`/workflows/library/save`):

```json
{
  "query": "agent observability",
  "context": {"user_id": "u1", "request_id": "req-123"},
  "paper_id": null,
  "top_k": 5
}
```

### Observability Event Standard

External event types are unified to:

- `request_started`
- `request_finished`
- `step_started`
- `step_finished`
- `tool_called`
- `tool_finished`
- `judge_finished`
- `error_raised`

Legacy node/workflow event names are normalized via mapping layer before recording.

### This Round Completed

- Added library workflow chain: search -> candidate select -> save_to_library -> compose -> observability.
- Added `/workflows/library/save` endpoint and completed workflow API set.
- Unified observability event emission points in node runner, tool wrapper, and judge nodes.
- Added integration and endpoint tests for library workflow and observability standard.

### Not Yet Productionized

- Java client transport still minimal and not integrated with advanced circuit-breaking / bulkhead controls.
- Workflow auth/rate-limit/multi-tenant isolation is not implemented.
- Observability sink is still in-memory and not persisted to external tracing backend.
