"""ワークフロー基盤の最小経路を検証する。"""

from __future__ import annotations

import pytest

from agent_core.shared.context import ExecutionContext
from agent_core.shared.preconditions import PreconditionError
from agent_core.shared.workflow import run_default_workflow


def test_default_workflow_runs_collect_and_validate() -> None:
    """入力収集→検証の最小経路が動作する。"""
    context = ExecutionContext(
        mode="profile",
        text_inputs=[],
        file_inputs=[],
        options={},
    )
    state = run_default_workflow(context)
    assert state.context == context
    assert state.warnings == [
        "collect_input not implemented",
        "validate not implemented",
    ]


def test_workflow_rejects_missing_job_inputs() -> None:
    """必須入力が無い場合は開始前にエラーとなる。"""
    context = ExecutionContext(
        mode="job",
        text_inputs=[],
        file_inputs=[],
        options={},
    )
    with pytest.raises(PreconditionError):
        run_default_workflow(context)
