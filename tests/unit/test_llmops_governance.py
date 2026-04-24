from domain.context import RequestContext
from domain.runtime import ModelConfig, ModelRoutingPolicy, PromptConfig
from evals.schemas import EvalRunInput
from evals.runners.tool_eval_runner import run_tool_eval
from evals.runners.workflow_eval_runner import run_workflow_eval
from integrations import get_model_router, get_prompt_registry, run_llm_task
from tools.academic.search_papers import SearchPapersInput, search_papers_tool
from tools.document.ask_paper import AskPaperInput, ask_paper_tool
from tools.document.fetch_pdf import FetchPdfInput, fetch_pdf_tool
from tools.document.index_document import IndexDocumentInput, index_document_tool
from tools.document.parse_pdf import ParsePdfInput, parse_pdf_tool


def test_prompt_registry_loads_default_and_explicit_versions():
    registry = get_prompt_registry()
    default_prompt = registry.load("ask_paper")
    explicit_prompt = registry.load("ask_paper", "v1")
    assert default_prompt.prompt_name == "ask_paper"
    assert default_prompt.prompt_version == "v1"
    assert explicit_prompt.prompt_version == "v1"
    assert "grounded evidence" in explicit_prompt.text


def test_model_routing_with_fallback_is_used():
    router = get_model_router()
    router.set_policy(
        ModelRoutingPolicy(
            task_type="fallback_test_task",
            primary_model="fail-primary-model",
            fallback_models=["mock-llm-fallback-v1"],
            enable_fallback=True,
        )
    )
    out = run_llm_task(
        task_type="fallback_test_task",
        prompt_name="ask_paper",
        prompt_version="v1",
        body="Question: why fallback?\nEvidence: none",
    )
    assert out.response.model_name == "mock-llm-fallback-v1"
    assert out.estimated_cost_usd >= 0
    assert out.response.token_usage.get("estimated_cost_microusd") is not None


def test_tool_meta_records_model_prompt_token_and_latency():
    ctx = RequestContext(user_id="u1", request_id="meta-ask-1")
    sr = search_papers_tool.execute(SearchPapersInput(context=ctx, query="llm", top_k=1))
    pid = sr.data["papers"][0]["paper_id"]
    fr = fetch_pdf_tool.execute(FetchPdfInput(context=ctx, paper_id=pid))
    doc_id = fr.data["document_id"]
    parse_pdf_tool.execute(ParsePdfInput(context=ctx, document_id=doc_id))
    index_document_tool.execute(IndexDocumentInput(context=ctx, document_id=doc_id))

    result = ask_paper_tool.execute(
        AskPaperInput(
            context=ctx,
            model=ModelConfig(provider="mock", model_name="mock-llm-v1"),
            prompt=PromptConfig(prompt_name="ask_paper", prompt_version="v1"),
            document_id=doc_id,
            question="what is the method?",
        )
    )
    assert result.success
    assert result.meta.model_name
    assert result.meta.prompt_name == "ask_paper"
    assert result.meta.prompt_version == "v1"
    assert result.meta.token_usage is None or "prompt_tokens" in result.meta.token_usage
    assert result.meta.latency_ms is not None


def test_eval_runners_generate_structured_results():
    tool_eval = run_tool_eval()
    assert tool_eval.total_samples >= 1
    assert tool_eval.completed_samples == tool_eval.total_samples
    assert len(tool_eval.sample_results) == tool_eval.total_samples
    assert "pass_rate" in tool_eval.metrics

    workflow_eval = run_workflow_eval()
    assert workflow_eval.total_samples >= 1
    assert workflow_eval.completed_samples == workflow_eval.total_samples
    assert len(workflow_eval.sample_results) == workflow_eval.total_samples
    assert "pass_rate" in workflow_eval.metrics


def test_eval_runners_support_prompt_model_comparison():
    tool_eval = run_tool_eval(
        EvalRunInput.model_validate(
            {
                "context": {"user_id": "eval-user", "request_id": "eval-compare-tool"},
                "dataset_name": "search_papers_basic",
                "dataset_version": "v1",
                "target_tool": "search_papers",
                "model": {"provider": "mock", "model_name": "mock-llm-v1"},
                "prompt": {"prompt_name": "ask_paper", "prompt_version": "v1"},
                "runtime": {"environment": "dev"},
            }
        ),
        model_variants=[
            {"provider": "mock", "model_name": "mock-llm-v1"},
            {"provider": "mock", "model_name": "mock-llm-fallback-v1"},
        ],
        prompt_variants=[
            {"prompt_name": "ask_paper", "prompt_version": "v1"},
            {"prompt_name": "compare_papers", "prompt_version": "v1"},
        ],
    )
    assert tool_eval.metrics["compare_rows_count"] >= 1

    workflow_eval = run_workflow_eval(
        model_variants=[
            {"provider": "mock", "model_name": "mock-llm-v1"},
            {"provider": "mock", "model_name": "mock-llm-fallback-v1"},
        ],
        prompt_variants=[
            {"prompt_name": "ask_paper", "prompt_version": "v1"},
            {"prompt_name": "compare_papers", "prompt_version": "v1"},
        ],
    )
    assert workflow_eval.metrics["compare_rows_count"] >= 1
    assert any(x.sample_id.startswith("compare::") for x in workflow_eval.sample_results)
