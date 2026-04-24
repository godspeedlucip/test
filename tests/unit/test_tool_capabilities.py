from tools.registry import get_tool_capability, get_tool_capability_map


def test_tool_capability_registry_exposes_metadata():
    caps = get_tool_capability_map()
    assert "record_observability_event" in caps
    assert caps["record_observability_event"].has_side_effect is True
    assert caps["record_observability_event"].name == "record_observability_event"
    assert caps["record_observability_event"].owner in {"python", "java", "platform"}


def test_side_effect_tool_capability_flags():
    assert get_tool_capability("save_paper_to_library").has_side_effect is True
    assert get_tool_capability("search_papers").has_side_effect is False
    assert get_tool_capability("save_paper_to_library").owner == "java"
