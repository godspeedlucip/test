from __future__ import annotations

from fastapi import Depends, FastAPI

from app.dependencies import get_settings
from graph.workflows.compare_export_workflow import build_compare_export_workflow
from graph.workflows.qa_workflow import build_qa_workflow

app = FastAPI(title="research_agent", version="0.1.0")


@app.get("/health")
def health(settings=Depends(get_settings)):
    return {"status": "ok", "app_name": settings.app_name}


@app.get("/observability/health")
def observability_health():
    return {"status": "ok"}


def run_demo() -> None:
    qa = build_qa_workflow()
    state = qa.invoke(
        {
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
