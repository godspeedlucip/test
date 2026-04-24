from domain.context import RequestContext
from tools.synthesis.compare_papers import ComparePapersInput, compare_papers_tool
from tools.synthesis.extract_paper_facts import ExtractPaperFactsInput, extract_paper_facts_tool

from graph.nodes.common import run_node


def compare_node(state: dict):
    def _impl(s: dict):
        ctx = RequestContext.model_validate(s.get("context", {"user_id": "anonymous"}))
        paper_ids = s.get("paper_ids", [])
        document_ids = s.get("document_ids", [])
        dimensions = s.get("compare_dimensions") or ["method", "dataset", "metrics", "limitations"]

        facts_by_paper: dict[str, dict] = {}
        all_evidences: list[dict] = []
        for idx, document_id in enumerate(document_ids):
            fact_result = extract_paper_facts_tool.execute(
                ExtractPaperFactsInput(
                    context=ctx,
                    model=s.get("model"),
                    prompt=s.get("prompt"),
                    runtime=s.get("runtime"),
                    document_id=document_id,
                    dimensions=dimensions,
                )
            )
            if not fact_result.success:
                raise RuntimeError(f"extract_paper_facts failed for {document_id}: {fact_result.error.message}")
            mapped_paper_id = paper_ids[idx] if idx < len(paper_ids) else fact_result.data["facts"]["paper_id"]
            fact_payload = dict(fact_result.data["facts"])
            fact_payload["paper_id"] = mapped_paper_id
            facts_by_paper[mapped_paper_id] = fact_payload
            all_evidences.extend(fact_payload.get("evidence_map", []))

        result = compare_papers_tool.execute(
            ComparePapersInput(
                context=ctx,
                model=s.get("model"),
                prompt=s.get("prompt"),
                runtime=s.get("runtime"),
                paper_ids=paper_ids,
                document_ids=document_ids,
                dimensions=dimensions,
                facts_by_paper=facts_by_paper,
            )
        )
        if not result.success:
            raise RuntimeError(f"compare_papers failed: {result.error.message}")
        return {
            "paper_facts": facts_by_paper,
            "comparison": result.data,
            "answer": result.data["summary"],
            "evidences": all_evidences,
            "llm_meta": result.meta.model_dump() if result.meta else None,
            "artifacts": s.get("artifacts", []) + [{"type": "comparison", "payload": result.data}],
        }

    return run_node("compare_node", state, _impl)
