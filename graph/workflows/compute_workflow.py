from langgraph.graph import END, START, StateGraph

from graph.nodes.compose_node import compose_node
from graph.nodes.compute_node import compute_node
from graph.nodes.observability_node import observability_node
from graph.state import AgentState


def build_compute_workflow():
    graph = StateGraph(AgentState)
    graph.add_node("compute_node", compute_node)
    graph.add_node("compose_node", compose_node)
    graph.add_node("observability_node", observability_node)

    graph.add_edge(START, "compute_node")
    graph.add_edge("compute_node", "compose_node")
    graph.add_edge("compose_node", "observability_node")
    graph.add_edge("observability_node", END)
    return graph.compile()
