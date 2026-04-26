from __future__ import annotations

from domain.context import RequestContext
from tools.academic.resolve_paper_identity import ResolvePaperIdentityInput, resolve_paper_identity_tool

from graph.nodes.common import run_node


def resolve_identity_node(state: dict):
    def _impl(s: dict):
        paper_ids = [pid for pid in (s.get("paper_ids") or []) if pid]
        if paper_ids:
            return {}

        query = s.get("query") or s.get("user_query") or s.get("question")
        if not query:
            return {}

        ctx = RequestContext.model_validate(s.get("context", {"user_id": "anonymous"}))
        resolved = resolve_paper_identity_tool.execute(ResolvePaperIdentityInput(context=ctx, query=query))
        if not resolved.success:
            return {}

        paper = resolved.data.get("paper") or {}
        paper_id = paper.get("paper_id")
        if not paper_id:
            return {}
        paper_details = dict(s.get("paper_details") or {})
        paper_details[paper_id] = paper
        return {"paper_ids": [paper_id], "paper_details": paper_details}

    return run_node("resolve_identity_node", state, _impl)
