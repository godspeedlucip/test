from langgraph.graph import END, START, StateGraph

from graph.nodes.compare_node import compare_node
from graph.nodes.compose_node import compose_node
from graph.nodes.export_node import export_node
from graph.nodes.intent_router import intent_router
from graph.nodes.judge_node import judge_node
from graph.nodes.observability_node import observability_node
from graph.nodes.prepare_documents import prepare_documents
from graph.state import GraphState


def build_compare_export_workflow():
    graph = StateGraph(GraphState)
    graph.add_node("intent_router", intent_router)
    graph.add_node("prepare_documents", prepare_documents)
    graph.add_node("compare_node", compare_node)
    graph.add_node("judge_node", judge_node)
    graph.add_node("export_node", export_node)
    graph.add_node("compose_node", compose_node)
    graph.add_node("observability_node", observability_node)

    graph.add_edge(START, "intent_router")
    graph.add_edge("intent_router", "prepare_documents")
    graph.add_edge("prepare_documents", "compare_node")
    graph.add_edge("compare_node", "judge_node")
    graph.add_edge("judge_node", "export_node")
    graph.add_edge("export_node", "compose_node")
    graph.add_edge("compose_node", "observability_node")
    graph.add_edge("observability_node", END)

    return graph.compile()
