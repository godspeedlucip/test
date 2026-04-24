from domain.context import RequestContext
from graph.workflows.compare_export_workflow import build_compare_export_workflow
from graph.workflows.library_workflow import build_library_workflow
from graph.workflows.qa_workflow import build_qa_workflow


def _step_names(state: dict) -> list[str]:
    return [step.get("node_name") for step in state.get("execution_steps", [])]


def test_real_workflow_qa_end_to_end_from_query():
    ctx = RequestContext(user_id="real-e2e-u1", request_id="real-e2e-qa")
    out = build_qa_workflow().invoke(
        {
            "workflow": "qa",
            "user_query": "What is the main method and contribution of this paper?",
            "context": ctx.model_dump(),
            "top_k": 1,
            "enable_judge": True,
        }
    )
    names = _step_names(out)
    assert out.get("final_answer")
    assert "search_node" in names
    assert "prepare_documents" in names
    assert "ask_node" in names
    assert "judge_node" in names


def test_real_workflow_compare_end_to_end_from_query():
    ctx = RequestContext(user_id="real-e2e-u2", request_id="real-e2e-compare")
    out = build_compare_export_workflow().invoke(
        {
            "workflow": "compare",
            "user_query": "Compare methods and datasets of recent agent papers.",
            "context": ctx.model_dump(),
            "top_k": 2,
            "enable_judge": True,
        }
    )
    names = _step_names(out)
    assert out.get("bibtex")
    assert "search_node" in names
    assert "prepare_documents" in names
    assert "compare_node" in names
    assert "judge_node" in names
    assert "export_node" in names


def test_real_workflow_library_save_end_to_end_from_query():
    ctx = RequestContext(user_id="real-e2e-u3", request_id="real-e2e-library")
    out = build_library_workflow().invoke(
        {
            "workflow": "library_save",
            "query": "retrieval augmented generation evaluation",
            "context": ctx.model_dump(),
            "top_k": 3,
        }
    )
    names = _step_names(out)
    assert out.get("saved_paper_id")
    assert out.get("save_result", {}).get("saved") is True
    assert "intent_router" in names
    assert "search_node" in names
    assert "choose_library_candidate_node" in names
    assert "save_library_node" in names

