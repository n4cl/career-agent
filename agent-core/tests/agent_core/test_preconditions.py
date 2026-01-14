"""CLI 入力の前提条件チェック."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_core.preconditions import (
    PreconditionError,
    validate_evaluate_preconditions,
    validate_job_preconditions,
    validate_profile_preconditions,
)


def test_profile_allows_empty_inputs() -> None:
    """プロフィールは空入力から対話を開始できる。"""
    validate_profile_preconditions(text_inputs=None, file_inputs=None)


def test_profile_rejects_unreadable_file() -> None:
    """プロフィールは読取不能なファイル入力を拒否する。"""
    missing = Path("/path/does/not/exist.txt")
    with pytest.raises(PreconditionError):
        validate_profile_preconditions(text_inputs=None, file_inputs=[missing])


def test_job_requires_at_least_one_file() -> None:
    """求人は1つ以上のファイル入力が必須。"""
    with pytest.raises(PreconditionError):
        validate_job_preconditions(file_inputs=None)


def test_job_accepts_readable_file(tmp_path: Path) -> None:
    """求人は読取可能なファイル入力を受け付ける。"""
    job_file = tmp_path / "job.txt"
    job_file.write_text("job")
    validate_job_preconditions(file_inputs=[job_file])


def test_evaluate_requires_both_paths(tmp_path: Path) -> None:
    """評価はプロフィールと求人の両パスが必須。"""
    profile_path = tmp_path / "profile.json"
    profile_path.write_text("{}")
    with pytest.raises(PreconditionError):
        validate_evaluate_preconditions(profile_path=profile_path, job_path=None)


def test_evaluate_rejects_unreadable_inputs(tmp_path: Path) -> None:
    """評価は読取不能な入力を拒否する。"""
    profile_path = tmp_path / "profile.json"
    profile_path.write_text("{}")
    missing = tmp_path / "missing.json"
    with pytest.raises(PreconditionError):
        validate_evaluate_preconditions(profile_path=profile_path, job_path=missing)


def test_evaluate_accepts_readable_inputs(tmp_path: Path) -> None:
    """評価は読取可能な入力を受け付ける。"""
    profile_path = tmp_path / "profile.json"
    job_path = tmp_path / "job.json"
    profile_path.write_text("{}")
    job_path.write_text("{}")
    validate_evaluate_preconditions(profile_path=profile_path, job_path=job_path)
