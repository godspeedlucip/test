from domain.context import RequestContext
from tools.synthesis.compare_papers import ComparePapersInput, compare_papers_tool
from tools.synthesis.extract_paper_facts import ExtractPaperFactsInput, extract_paper_facts_tool
from tools.synthesis.generate_related_work import GenerateRelatedWorkInput, generate_related_work_tool

from graph.nodes.common import run_node


def related_work_node(state: dict):
    def _impl(s: dict):
        ctx = RequestContext.model_validate(s.get("context", {"user_id": "anonymous"}))
        paper_ids = s.get("paper_ids", [])
        document_ids = s.get("document_ids", [])
        if not paper_ids:
            raise RuntimeError("related_work_node requires paper_ids")
        if not document_ids:
            raise RuntimeError("related_work_node requires document_ids; run prepare_documents first")

        dimensions = s.get("compare_dimensions") or ["method", "dataset", "metrics", "limitations"]
        facts_by_paper: dict[str, dict] = {}
        evidences: list[dict] = []

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
            evidences.extend(fact_payload.get("evidence_map", []))

        comparison_result = compare_papers_tool.execute(
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
        if not comparison_result.success:
            raise RuntimeError(f"compare_papers failed: {comparison_result.error.message}")

        topic = s.get("topic") or s.get("question") or s.get("user_query", "related work")
        related_result = generate_related_work_tool.execute(
            GenerateRelatedWorkInput(
                context=ctx,
                model=s.get("model"),
                prompt=s.get("prompt"),
                runtime=s.get("runtime"),
                paper_ids=paper_ids,
                topic=topic,
                target_length=s.get("target_length", "medium"),
                require_citations=s.get("require_citations", True),
                comparison=comparison_result.data,
                paper_facts=facts_by_paper,
            )
        )
        if not related_result.success:
            raise RuntimeError(f"generate_related_work failed: {related_result.error.message}")

        for spans in related_result.data.get("evidence_map", {}).values():
            evidences.extend(spans)

        llm_meta = related_result.meta.model_dump() if related_result.meta else None
        return {
            "paper_facts": facts_by_paper,
            "comparison": comparison_result.data,
            "related_work": related_result.data,
            "answer": related_result.data["related_work_text"],
            "evidences": evidences,
            "llm_meta": llm_meta,
            "artifacts": s.get("artifacts", [])
            + [
                {"type": "related_work_input_summary", "payload": {"paper_count": len(paper_ids), "topic": topic}},
                {"type": "comparison", "payload": comparison_result.data},
                {"type": "related_work", "payload": related_result.data},
            ],
        }

    return run_node("related_work_node", state, _impl)
