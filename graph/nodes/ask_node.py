from domain.context import RequestContext
from tools.document.ask_paper import AskPaperInput, ask_paper_tool

from graph.nodes.common import run_node


def ask_node(state: dict):
    def _impl(s: dict):
        ctx = RequestContext.model_validate(s.get("context", {"user_id": "anonymous"}))
        doc_id = (s.get("document_ids") or [None])[0]
        if not doc_id:
            raise RuntimeError("ask_node: missing document_id")
        result = ask_paper_tool.execute(
            AskPaperInput(
                context=ctx,
                model=s.get("model"),
                prompt=s.get("prompt"),
                runtime=s.get("runtime"),
                document_id=doc_id,
                question=s.get("question") or s.get("user_query", ""),
            )
        )
        if not result.success:
            raise RuntimeError(result.error.message if result.error else "ask_paper failed")
        return {
            "answer": result.data["answer"],
            "evidences": result.data["evidences"],
            "llm_meta": result.meta.model_dump() if result.meta else None,
            "artifacts": s.get("artifacts", []) + [{"type": "qa", "payload": result.data}],
        }

    return run_node("ask_node", state, _impl)
