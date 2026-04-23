from observability.recorder import get_recorder

from graph.nodes.common import run_node


def observability_node(state: dict):
    def _impl(s: dict):
        recorder = get_recorder()
        recorder.emit(
            event_type="request_finished",
            trace_id=s.get("trace_id", "unknown"),
            payload={"has_error": bool(s.get("errors")), "artifacts": len(s.get("artifacts", []))},
        )
        return {}

    return run_node("observability_node", state, _impl)
