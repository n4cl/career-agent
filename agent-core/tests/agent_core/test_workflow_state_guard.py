"""ワークフローの状態更新ガードを検証する。"""

from __future__ import annotations

import pytest

from agent_core.context import ExecutionContext
from agent_core.workflow import WorkflowState, guard_node


def test_guard_rejects_unintended_context_mutation() -> None:
    """許可されていない状態変更は拒否する。"""
    context = ExecutionContext(
        mode="profile",
        text_inputs=["a"],
        file_inputs=[],
        options={},
    )
    state = WorkflowState(context=context)

    def mutate_context(target: WorkflowState) -> WorkflowState:
        new_context = ExecutionContext(
            mode="profile",
            text_inputs=["b"],
            file_inputs=[],
            options={},
        )
        return WorkflowState(context=new_context, warnings=target.warnings)

    guarded = guard_node(mutate_context, allowed_fields={"warnings"})
    with pytest.raises(ValueError):
        guarded(state)


def test_guard_allows_warning_updates() -> None:
    """許可された警告更新は通る。"""
    context = ExecutionContext(
        mode="profile",
        text_inputs=[],
        file_inputs=[],
        options={},
    )
    state = WorkflowState(context=context)

    def append_warning(target: WorkflowState) -> WorkflowState:
        target.warnings.append("warn")
        return target

    guarded = guard_node(append_warning, allowed_fields={"warnings"})
    result = guarded(state)
    assert result.warnings == ["warn"]
