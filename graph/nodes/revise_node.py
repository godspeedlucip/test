from graph.nodes.common import run_node


def revise_node(state: dict):
    def _impl(_: dict):
        return {}

    return run_node("revise_node", state, _impl)
