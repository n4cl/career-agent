"""CLI input precondition checks."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
import os


class PreconditionError(ValueError):
    """Raised when required CLI inputs are missing or unreadable."""


def _ensure_readable_paths(paths: Sequence[Path], *, label: str) -> None:
    """Validate that all paths exist and are readable files."""
    for path in paths:
        if not path.exists() or not path.is_file() or not os.access(path, os.R_OK):
            raise PreconditionError(f"{label} input is not readable: {path}")


def validate_profile_preconditions(
    *,
    text_inputs: Sequence[str] | None,
    file_inputs: Sequence[Path] | None,
) -> None:
    """Validate profile inputs; empty input is allowed to start interviews."""
    if file_inputs:
        _ensure_readable_paths(file_inputs, label="profile")



def validate_job_preconditions(*, file_inputs: Sequence[Path] | None) -> None:
    """Validate job inputs; at least one readable file is required."""
    if not file_inputs:
        raise PreconditionError("job input is required")
    _ensure_readable_paths(file_inputs, label="job")



def validate_evaluate_preconditions(
    *,
    profile_path: Path | None,
    job_path: Path | None,
) -> None:
    """Validate evaluation inputs; profile and job paths are required."""
    if profile_path is None or job_path is None:
        raise PreconditionError("profile and job inputs are required")
    _ensure_readable_paths([profile_path], label="profile")
    _ensure_readable_paths([job_path], label="job")
