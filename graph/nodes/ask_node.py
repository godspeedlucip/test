from domain.context import RequestContext
from tools.document.ask_paper import AskPaperInput, ask_paper_tool

from graph.nodes.common import run_node


def ask_node(state: dict):
    def _impl(s: dict):
        ctx = RequestContext.model_validate(s.get("context", {"user_id": "anonymous"}))
        doc_id = (s.get("document_ids") or [None])[0]
        if not doc_id:
            return {"errors": s.get("errors", []) + ["ask_node: missing document_id"]}
        result = ask_paper_tool.execute(
            AskPaperInput(
                context=ctx,
                model=s.get("model"),
                prompt=s.get("prompt"),
                document_id=doc_id,
                question=s.get("question") or s.get("user_query", ""),
            )
        )
        if not result.success:
            return {"errors": s.get("errors", []) + [result.error.message]}
        return {
            "answer": result.data["answer"],
            "evidences": result.data["evidences"],
            "artifacts": s.get("artifacts", []) + [{"type": "qa", "payload": result.data}],
        }

    return run_node("ask_node", state, _impl)
