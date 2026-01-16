"""CLI 入力の前提条件チェック."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
import os


class PreconditionError(ValueError):
    """必須入力が欠けている、または読取不能な場合に送出する。"""


def _ensure_readable_paths(paths: Sequence[Path], *, label: str) -> None:
    """すべてのパスが存在し、読み取り可能なファイルか検証する。"""
    for path in paths:
        if not path.exists() or not path.is_file() or not os.access(path, os.R_OK):
            raise PreconditionError(f"{label} input is not readable: {path}")


def validate_profile_preconditions(
    *,
    text_inputs: Sequence[str] | None,
    file_inputs: Sequence[Path] | None,
) -> None:
    """プロフィール入力を検証する（空入力でも対話開始を許容）。"""
    if file_inputs:
        _ensure_readable_paths(file_inputs, label="profile")



def validate_job_preconditions(*, file_inputs: Sequence[Path] | None) -> None:
    """求人入力を検証する（読み取り可能なファイルが必須）。"""
    if not file_inputs:
        raise PreconditionError("job input is required")
    _ensure_readable_paths(file_inputs, label="job")



def validate_evaluate_preconditions(
    *,
    profile_path: Path | None,
    job_path: Path | None,
) -> None:
    """評価入力を検証する（プロフィールと求人の両方が必須）。"""
    if profile_path is None or job_path is None:
        raise PreconditionError("profile and job inputs are required")
    _ensure_readable_paths([profile_path], label="profile")
    _ensure_readable_paths([job_path], label="job")
