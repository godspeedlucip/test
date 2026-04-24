from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi import HTTPException

from app.api_schemas import (
    CompareWorkflowRequest,
    LibraryManageWorkflowRequest,
    LibraryManageWorkflowResponse,
    LibrarySaveWorkflowRequest,
    LibrarySaveWorkflowResponse,
    QaWorkflowRequest,
    RelatedWorkWorkflowRequest,
    WorkflowBaseResponse,
)
from app.dependencies import get_settings
from graph.workflows.compare_export_workflow import build_compare_export_workflow
from graph.workflows.library_workflow import build_library_workflow
from graph.workflows.library_manage_workflow import build_library_manage_workflow
from graph.workflows.qa_workflow import build_qa_workflow
from graph.workflows.related_work_workflow import build_related_work_workflow

app = FastAPI(title="research_agent", version="0.1.0")


@app.get("/health")
def health(settings=Depends(get_settings)):
    return {"status": "ok", "app_name": settings.app_name}


@app.get("/observability/health")
def observability_health():
    return {"status": "ok"}


def _invoke_workflow(workflow, state: dict) -> dict:
    result = workflow.invoke(state)
    return {
        "trace_id": result.get("trace_id"),
        "final_answer": result.get("final_answer"),
        "errors": result.get("errors", []),
        "execution_steps": result.get("execution_steps", []),
        **result,
    }


@app.post("/workflows/qa", response_model=WorkflowBaseResponse)
def run_qa_workflow(payload: QaWorkflowRequest):
    app_graph = build_qa_workflow()
    result = _invoke_workflow(
        app_graph,
        {
            "workflow": "qa",
            "user_query": payload.user_query,
            "context": payload.context.model_dump(),
            "paper_ids": payload.paper_ids,
            "enable_judge": payload.enable_judge,
        },
    )
    return WorkflowBaseResponse.model_validate(result)


@app.post("/workflows/compare", response_model=WorkflowBaseResponse)
def run_compare_workflow(payload: CompareWorkflowRequest):
    app_graph = build_compare_export_workflow()
    result = _invoke_workflow(
        app_graph,
        {
            "workflow": "compare",
            "user_query": payload.user_query,
            "context": payload.context.model_dump(),
            "paper_ids": payload.paper_ids,
            "enable_judge": payload.enable_judge,
        },
    )
    return WorkflowBaseResponse.model_validate(result)


@app.post("/workflows/related-work", response_model=WorkflowBaseResponse)
def run_related_workflow(payload: RelatedWorkWorkflowRequest):
    app_graph = build_related_work_workflow()
    result = _invoke_workflow(
        app_graph,
        {
            "workflow": "related_work",
            "user_query": payload.user_query,
            "topic": payload.topic,
            "context": payload.context.model_dump(),
            "paper_ids": payload.paper_ids,
            "enable_judge": payload.enable_judge,
            "max_revise": payload.max_revise,
        },
    )
    return WorkflowBaseResponse.model_validate(result)


@app.post("/workflows/library/save", response_model=LibrarySaveWorkflowResponse)
def run_library_save_workflow(payload: LibrarySaveWorkflowRequest):
    app_graph = build_library_workflow()
    result = _invoke_workflow(
        app_graph,
        {
            "workflow": "library_save",
            "query": payload.query,
            "context": payload.context.model_dump(),
            "paper_id": payload.paper_id,
            "top_k": payload.top_k,
        },
    )
    return LibrarySaveWorkflowResponse.model_validate(result)


@app.post("/workflows/library/manage", response_model=LibraryManageWorkflowResponse)
def run_library_manage_workflow(payload: LibraryManageWorkflowRequest):
    if payload.action in {"save", "add_note", "tag"} and not payload.idempotency_key:
        raise HTTPException(status_code=400, detail="idempotency_key is required for save/add_note/tag actions")
    app_graph = build_library_manage_workflow()
    context = payload.context.model_dump()
    if payload.idempotency_key:
        context["request_id"] = payload.idempotency_key
    result = _invoke_workflow(
        app_graph,
        {
            "workflow": "library_manage",
            "action": payload.action,
            "query": payload.query,
            "context": context,
            "paper_id": payload.paper_id,
            "top_k": payload.top_k,
            "library_note": payload.library_note,
            "paper_tags": payload.paper_tags,
            "idempotency_key": payload.idempotency_key,
        },
    )
    return LibraryManageWorkflowResponse.model_validate(result)


def run_demo() -> None:
    qa = build_qa_workflow()
    state = qa.invoke(
        {
            "workflow": "qa",
            "user_query": "What is the method in this paper?",
            "context": {"user_id": "demo", "request_id": "req-demo-qa"},
            "paper_ids": ["oa-1"],
            "enable_judge": True,
        }
    )
    print("QA FINAL:", state.get("final_answer"))

    compare = build_compare_export_workflow()
    state2 = compare.invoke(
        {
            "workflow": "compare",
            "user_query": "Compare these papers",
            "context": {"user_id": "demo", "request_id": "req-demo-cmp"},
            "paper_ids": ["oa-1", "oa-2"],
            "enable_judge": True,
        }
    )
    print("COMPARE FINAL:", state2.get("final_answer"))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)
