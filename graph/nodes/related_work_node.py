from graph.nodes.common import run_node


def related_work_node(state: dict):
    def _impl(_: dict):
        return {"errors": ["related_work_node not implemented in phase 1"]}

    return run_node("related_work_node", state, _impl)
