from langgraph.graph import END, START, StateGraph

from graph.nodes.choose_library_candidate_node import choose_library_candidate_node
from graph.nodes.library_compose_node import library_compose_node
from graph.nodes.library_search_node import library_search_node
from graph.nodes.observability_node import observability_node
from graph.nodes.save_library_node import save_library_node
from graph.state import GraphState


def build_library_workflow():
    graph = StateGraph(GraphState)
    graph.add_node("library_search_node", library_search_node)
    graph.add_node("choose_library_candidate_node", choose_library_candidate_node)
    graph.add_node("save_library_node", save_library_node)
    graph.add_node("library_compose_node", library_compose_node)
    graph.add_node("observability_node", observability_node)

    graph.add_edge(START, "library_search_node")
    graph.add_edge("library_search_node", "choose_library_candidate_node")
    graph.add_edge("choose_library_candidate_node", "save_library_node")
    graph.add_edge("save_library_node", "library_compose_node")
    graph.add_edge("library_compose_node", "observability_node")
    graph.add_edge("observability_node", END)

    return graph.compile()
