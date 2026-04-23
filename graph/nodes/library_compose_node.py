from graph.nodes.common import run_node


def library_compose_node(state: dict):
    def _impl(s: dict):
        selected = s.get("selected_paper_id")
        candidates = s.get("library_candidates", [])
        total_candidates = len(candidates)
        return {
            "final_answer": f"Saved paper {selected} to library. Candidates considered: {total_candidates}.",
        }

    return run_node("library_compose_node", state, _impl)
