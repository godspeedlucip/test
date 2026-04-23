from domain.context import RequestContext
from tools.academic.search_papers import SearchPapersInput, search_papers_tool

from graph.nodes.common import run_node


def library_search_node(state: dict):
    def _impl(s: dict):
        ctx = RequestContext.model_validate(s.get("context", {"user_id": "anonymous"}))
        query = s.get("query") or s.get("user_query")
        if not query:
            raise RuntimeError("library_search_node requires query")
        top_k = int(s.get("top_k", 5))
        result = search_papers_tool.execute(SearchPapersInput(context=ctx, query=query, top_k=top_k))
        if not result.success:
            raise RuntimeError(result.error.message if result.error else "search_papers failed")
        papers = result.data.get("papers", [])
        return {
            "library_search_result": result.data,
            "library_candidates": papers,
            "paper_ids": [p.get("paper_id") for p in papers if p.get("paper_id")],
        }

    return run_node("library_search_node", state, _impl)
