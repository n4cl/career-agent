"""LangGraph によるワークフロー基盤."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from langgraph.graph import StateGraph

from .context import ExecutionContext
from .preconditions import (
    PreconditionError,
    validate_evaluate_preconditions,
    validate_job_preconditions,
    validate_profile_preconditions,
)


@dataclass
class WorkflowState:
    """ワークフロー内で共有する状態."""

    context: ExecutionContext
    warnings: list[str] = field(default_factory=list)


Node = Callable[[WorkflowState], WorkflowState]


def _snapshot_state(state: WorkflowState) -> dict[str, object]:
    """比較のために状態をスナップショットする。"""
    return {
        "context": state.context,
        "warnings": list(state.warnings),
    }


def guard_node(node: Node, *, allowed_fields: set[str]) -> Node:
    """許可されたフィールド以外の変更を検出して拒否する。"""

    def _run(state: WorkflowState) -> WorkflowState:
        before = _snapshot_state(state)
        result = node(state)
        if not isinstance(result, WorkflowState):
            raise ValueError("workflow node must return WorkflowState")
        after = _snapshot_state(result)
        for field_name, before_value in before.items():
            if field_name in allowed_fields:
                continue
            if after[field_name] != before_value:
                raise ValueError(f"unauthorized state mutation: {field_name}")
        return result

    return _run


def _default_node(name: str) -> Node:
    """未実装ノードは警告を残して状態を返す。"""

    def _run(state: WorkflowState) -> WorkflowState:
        state.warnings.append(f"{name} not implemented")
        return state

    return _run


def _validate_prerequisites(context: ExecutionContext) -> None:
    """ワークフロー開始前に前提条件を検証する。"""
    if context.mode == "profile":
        validate_profile_preconditions(
            text_inputs=context.text_inputs,
            file_inputs=context.file_inputs,
        )
        return
    if context.mode == "job":
        validate_job_preconditions(file_inputs=context.file_inputs)
        return
    if context.mode == "evaluate":
        profile_path = context.options.get("profile_path")
        job_path = context.options.get("job_path")
        validate_evaluate_preconditions(
            profile_path=profile_path,
            job_path=job_path,
        )
        return
    raise PreconditionError(f"unsupported mode: {context.mode}")


def build_default_workflow(
    *,
    collect_node: Node | None = None,
    validate_node: Node | None = None,
) -> StateGraph:
    """入力収集→検証の最小経路を持つワークフローを構築する。"""
    graph = StateGraph(WorkflowState)

    collect = collect_node or _default_node("collect_input")
    validate = validate_node or _default_node("validate")

    graph.add_node("collect_input", guard_node(collect, allowed_fields={"warnings"}))
    graph.add_node("validate", guard_node(validate, allowed_fields={"warnings"}))

    graph.set_entry_point("collect_input")
    graph.add_edge("collect_input", "validate")
    graph.set_finish_point("validate")

    return graph


def run_default_workflow(
    context: ExecutionContext,
    *,
    collect_node: Node | None = None,
    validate_node: Node | None = None,
) -> WorkflowState:
    """最小ワークフローを実行して状態を返す。"""
    _validate_prerequisites(context)
    graph = build_default_workflow(collect_node=collect_node, validate_node=validate_node)
    compiled = graph.compile()
    state = WorkflowState(context=context)
    result = compiled.invoke(state)
    if isinstance(result, WorkflowState):
        return result
    return WorkflowState(**result)
