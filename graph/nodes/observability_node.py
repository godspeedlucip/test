from graph.nodes.common import run_node


def observability_node(state: dict):
    def _impl(s: dict):
        return {
            "observability_summary": {
                "has_error": bool(s.get("errors")),
                "artifacts": len(s.get("artifacts", [])),
                "steps": len(s.get("execution_steps", [])),
                "checkpoints": len(s.get("checkpoints", [])),
            }
        }

    return run_node("observability_node", state, _impl)
