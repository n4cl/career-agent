from __future__ import annotations

from functools import partial

import pytest
from langgraph.graph import StateGraph

from profile_agent.workflow.graph import build_profile_workflow
from profile_agent.workflow.state import ProfileState


def test_build_profile_workflow_returns_state_graph() -> None:
    """プロフィール用 LangGraph が StateGraph を返すかを検証する。"""
    graph = build_profile_workflow()
    assert isinstance(graph, StateGraph)


def test_profile_state_requires_core_keys() -> None:
    """ProfileState の必須キーが欠けるとバリデーションが失敗することを確認。"""
    with pytest.raises(ValueError):
        ProfileState(mode="create")


def test_workflow_can_inject_custom_nodes(mock_node) -> None:
    """外部ノードを差し込めるよう差し替え用フックがあることを検証する。"""
    graph = build_profile_workflow(
        collect_input_factory=partial(mock_node, name="collect"),
        validate_factory=partial(mock_node, name="validate"),
    )
    assert graph.state_schema == ProfileState


@pytest.fixture
def mock_node():
    """LangGraph ノード差し替え用の簡易モック."""

    def _factory(*_, **kwargs):
        return lambda state: state | {"mock": kwargs.get("name")}

    return _factory
