from domain.context import RequestContext
from tools.citation.export_bibtex import ExportBibtexInput, export_bibtex_tool

from graph.nodes.common import run_node


def export_node(state: dict):
    def _impl(s: dict):
        ctx = RequestContext.model_validate(s.get("context", {"user_id": "anonymous"}))
        result = export_bibtex_tool.execute(ExportBibtexInput(context=ctx, paper_ids=s.get("paper_ids", [])))
        if not result.success:
            return {"errors": s.get("errors", []) + [result.error.message]}
        return {
            "bibtex": result.data,
            "artifacts": s.get("artifacts", []) + [{"type": "bibtex", "payload": result.data}],
        }

    return run_node("export_node", state, _impl)
