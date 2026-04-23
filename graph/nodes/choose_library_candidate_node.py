from graph.nodes.common import run_node


def choose_library_candidate_node(state: dict):
    def _impl(s: dict):
        candidates = s.get("library_candidates", [])
        if not candidates:
            raise RuntimeError("no candidate papers found")

        explicit_paper_id = s.get("paper_id")
        if explicit_paper_id:
            for candidate in candidates:
                if candidate.get("paper_id") == explicit_paper_id:
                    return {"selected_paper_id": explicit_paper_id}
            raise RuntimeError(f"requested paper_id not found in candidates: {explicit_paper_id}")

        return {"selected_paper_id": candidates[0]["paper_id"]}

    return run_node("choose_library_candidate_node", state, _impl)
