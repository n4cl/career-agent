"""前提エラーの内容を検証する。"""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_core.shared.preconditions import PreconditionError


def test_job_error_message_explains_missing_input() -> None:
    """求人の前提エラーに不足内容が含まれる。"""
    with pytest.raises(PreconditionError) as excinfo:
        from agent_core.shared.preconditions import validate_job_preconditions

        validate_job_preconditions(file_inputs=None)

    assert "job input" in str(excinfo.value)


def test_evaluate_error_message_explains_missing_inputs(tmp_path: Path) -> None:
    """評価の前提エラーに不足内容が含まれる。"""
    profile_path = tmp_path / "profile.json"
    profile_path.write_text("{}")
    with pytest.raises(PreconditionError) as excinfo:
        from agent_core.shared.preconditions import validate_evaluate_preconditions

        validate_evaluate_preconditions(profile_path=profile_path, job_path=None)

    assert "profile" in str(excinfo.value)
    assert "job" in str(excinfo.value)
