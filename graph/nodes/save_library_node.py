from domain.context import RequestContext
from tools.library.save_paper_to_library import SavePaperToLibraryInput, save_paper_to_library_tool

from graph.nodes.common import run_node


def save_library_node(state: dict):
    def _impl(s: dict):
        ctx = RequestContext.model_validate(s.get("context", {"user_id": "anonymous"}))
        paper_id = s.get("selected_paper_id")
        if not paper_id:
            raise RuntimeError("selected_paper_id is required before save")

        result = save_paper_to_library_tool.execute(SavePaperToLibraryInput(context=ctx, paper_id=paper_id))
        if not result.success:
            raise RuntimeError(result.error.message if result.error else "save_paper_to_library failed")

        return {
            "saved_paper_id": paper_id,
            "save_result": result.data,
            "artifacts": s.get("artifacts", []) + [{"type": "library_save", "payload": {"paper_id": paper_id}}],
        }

    return run_node("save_library_node", state, _impl)
