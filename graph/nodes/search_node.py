from __future__ import annotations

from domain.context import RequestContext
from tools.academic.get_paper_details import GetPaperDetailsInput, get_paper_details_tool
from tools.academic.search_papers import SearchPapersInput, search_papers_tool

from graph.nodes.common import run_node


def search_node(state: dict):
    def _impl(s: dict):
        hinted_paper_ids = [pid for pid in (s.get("paper_ids") or []) if pid]
        query = s.get("query") or s.get("user_query") or s.get("question")
        ctx = RequestContext.model_validate(s.get("context", {"user_id": "anonymous"}))
        papers: list[dict] = []
        if query:
            result = search_papers_tool.execute(
                SearchPapersInput(
                    context=ctx,
                    runtime=s.get("runtime"),
                    query=query,
                    authors=s.get("authors") or [],
                    year_from=s.get("year_from"),
                    year_to=s.get("year_to"),
                    venue=s.get("venue"),
                    top_k=int(s.get("top_k", 10) or 10),
                    sources=s.get("sources") or ["openalex", "crossref", "arxiv"],
                )
            )
            if not result.success:
                raise RuntimeError(result.error.message if result.error else "search_papers failed")
            papers = list(result.data.get("papers", []))

        enriched_hint_papers: list[dict] = []
        for hinted_paper_id in hinted_paper_ids:
            detail = get_paper_details_tool.execute(GetPaperDetailsInput(context=ctx, paper_id=hinted_paper_id))
            if detail.success:
                enriched_hint_papers.append(detail.data["paper"])

        if hinted_paper_ids and papers:
            hinted_set = set(hinted_paper_ids)
            filtered = [paper for paper in papers if paper.get("paper_id") in hinted_set]
            if filtered:
                papers = filtered
            for hinted in enriched_hint_papers:
                if hinted.get("paper_id") and all(x.get("paper_id") != hinted["paper_id"] for x in papers):
                    papers.append(hinted)
        elif hinted_paper_ids and not papers:
            papers = enriched_hint_papers

        unique_papers: list[dict] = []
        seen: set[str] = set()
        for paper in papers:
            paper_id = paper.get("paper_id")
            if not paper_id or paper_id in seen:
                continue
            seen.add(paper_id)
            unique_papers.append(paper)

        return {
            "query": query,
            "retrieved_papers": unique_papers,
            "paper_ids": [p.get("paper_id") for p in unique_papers if p.get("paper_id")],
            "library_candidates": unique_papers,
            "library_search_result": {
                "query": query,
                "papers": unique_papers,
                "hinted_paper_ids": hinted_paper_ids,
            },
        }

    return run_node("search_node", state, _impl)
