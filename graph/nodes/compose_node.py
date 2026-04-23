from graph.nodes.common import run_node


def compose_node(state: dict):
    def _impl(s: dict):
        if s.get("comparison"):
            text = s["comparison"].get("summary", "")
        else:
            text = s.get("answer", "")
        if s.get("judge_results"):
            score = s["judge_results"][-1].get("overall_score")
            text = f"{text}\n\n[Judge overall_score={score}]"
        if s.get("bibtex"):
            text = f"{text}\n\nBibTeX entries: {s['bibtex'].get('entries_count', 0)}"
        return {"final_answer": text}

    return run_node("compose_node", state, _impl)
