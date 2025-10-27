"""LangGraph ワークフローの構築処理."""

from __future__ import annotations

from collections.abc import Callable

from langgraph.graph import StateGraph

from .nodes.collect_input import collect_input_node
from .state import ProfileState

NodeFactory = Callable[[], Callable[[ProfileState], ProfileState]]


def _default_node(name: str) -> Callable[[ProfileState], ProfileState]:
    """デフォルトでは警告を残してステートを返す no-op ノード."""

    def _runner(state: ProfileState) -> ProfileState:
        state.warnings.append(f"{name} not implemented")
        return state

    return _runner


def build_profile_workflow(
    *,
    collect_input_factory: NodeFactory | None = None,
    validate_factory: NodeFactory | None = None,
) -> StateGraph:
    """プロフィール管理フロー用の LangGraph を組み立てる."""
    graph = StateGraph(ProfileState)

    collect_node = (collect_input_factory or collect_input_node)()
    validate_node = (validate_factory or (lambda: _default_node("validate")))()

    graph.add_node("collect_input", collect_node)
    graph.add_node("validate_profile", validate_node)

    graph.set_entry_point("collect_input")
    graph.add_edge("collect_input", "validate_profile")
    graph.set_finish_point("validate_profile")

    return graph
