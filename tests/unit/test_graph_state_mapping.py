from graph.state import AgentState


def test_graph_state_aliases_agent_state():
    state = AgentState(
        workflow="qa",
        user_query="q",
        trace_id="t-1",
        working_document_ids=["d1"],
    )
    assert state.workflow == "qa"
    assert state.trace_id == "t-1"
    assert state.working_document_ids == ["d1"]
