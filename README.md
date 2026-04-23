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
