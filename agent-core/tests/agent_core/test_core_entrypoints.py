"""コアロジックの呼び出し口を検証する。"""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_core.core import CoreAgentService
from agent_core.shared.context import ExecutionContext


def test_core_service_exposes_profile_entrypoint() -> None:
    """プロフィールの入口が存在する。"""
    service = CoreAgentService()
    context = ExecutionContext(
        mode="profile",
        text_inputs=[],
        file_inputs=[],
        options={},
        run_id="run-1",
    )
    result = service.run_profile(context)
    assert result.mode == "profile"


def test_core_service_exposes_job_entrypoint(tmp_path: Path) -> None:
    """求人の入口が存在する。"""
    service = CoreAgentService()
    job_file = tmp_path / "job.txt"
    job_file.write_text("job")
    context = ExecutionContext(
        mode="job",
        text_inputs=[],
        file_inputs=[job_file],
        options={},
        run_id="run-1",
    )
    result = service.run_job(context)
    assert result.mode == "job"


def test_core_service_exposes_evaluate_entrypoint(tmp_path: Path) -> None:
    """評価の入口が存在する。"""
    service = CoreAgentService()
    profile_path = tmp_path / "profile.json"
    job_path = tmp_path / "job.json"
    profile_path.write_text("{}")
    job_path.write_text("{}")
    context = ExecutionContext(
        mode="evaluate",
        text_inputs=[],
        file_inputs=[],
        options={"profile_path": profile_path, "job_path": job_path},
        run_id="run-1",
    )
    result = service.run_evaluate(context)
    assert result.mode == "evaluate"


def test_core_service_rejects_mismatched_context() -> None:
    """入口と実行モードが一致しない場合は拒否する。"""
    service = CoreAgentService()
    context = ExecutionContext(
        mode="job",
        text_inputs=[],
        file_inputs=[],
        options={},
        run_id="run-1",
    )
    with pytest.raises(ValueError):
        service.run_profile(context)
