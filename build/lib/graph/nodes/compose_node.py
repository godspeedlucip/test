from domain.context import RequestContext
from tools.citation.format_references import FormatReferencesInput, format_references_tool

from graph.nodes.common import run_node


def compose_node(state: dict):
    def _impl(s: dict):
        if s.get("related_work"):
            text = s["related_work"].get("related_work_text", "")
        elif s.get("comparison"):
            text = s["comparison"].get("summary", "")
        else:
            text = s.get("answer", "")

        if s.get("judge_results"):
            score = s["judge_results"][-1].get("overall_score")
            text = f"{text}\n\n[Judge overall_score={score}]"
        if s.get("human_review"):
            text = f"{text}\n\n[Human review required: {s['human_review'].get('reason', 'pending')}]"
        if s.get("bibtex"):
            text = f"{text}\n\nBibTeX entries: {s['bibtex'].get('entries_count', 0)}"

        ctx = RequestContext.model_validate(s.get("context", {"user_id": "anonymous"}))
        references = list(s.get("references") or [])
        if not references and s.get("paper_details"):
            references = [p.get("title", pid) for pid, p in s.get("paper_details", {}).items()]
        if references:
            formatted = format_references_tool.execute(FormatReferencesInput(context=ctx, references=references))
            if formatted.success:
                refs = formatted.data.get("formatted", [])
                text = f"{text}\n\nReferences:\n" + "\n".join(f"- {x}" for x in refs)
                return {"final_answer": text, "formatted_references": refs}
        return {"final_answer": text}

    return run_node("compose_node", state, _impl)
