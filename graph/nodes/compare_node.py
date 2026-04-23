from domain.context import RequestContext
from tools.synthesis.compare_papers import ComparePapersInput, compare_papers_tool

from graph.nodes.common import run_node


def compare_node(state: dict):
    def _impl(s: dict):
        ctx = RequestContext.model_validate(s.get("context", {"user_id": "anonymous"}))
        result = compare_papers_tool.execute(
            ComparePapersInput(
                context=ctx,
                model=s.get("model"),
                prompt=s.get("prompt"),
                paper_ids=s.get("paper_ids", []),
                document_ids=s.get("document_ids", []),
                dimensions=s.get("compare_dimensions") or ["method", "dataset", "metrics"],
            )
        )
        if not result.success:
            return {"errors": s.get("errors", []) + [result.error.message]}
        return {
            "comparison": result.data,
            "answer": result.data["summary"],
            "artifacts": s.get("artifacts", []) + [{"type": "comparison", "payload": result.data}],
        }

    return run_node("compare_node", state, _impl)
