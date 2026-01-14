"""Precondition checks for CLI inputs."""

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
    """Profile preconditions allow empty input to start interviews."""
    validate_profile_preconditions(text_inputs=None, file_inputs=None)


def test_profile_rejects_unreadable_file() -> None:
    """Profile preconditions reject unreadable file inputs."""
    missing = Path("/path/does/not/exist.txt")
    with pytest.raises(PreconditionError):
        validate_profile_preconditions(text_inputs=None, file_inputs=[missing])


def test_job_requires_at_least_one_file() -> None:
    """Job preconditions require at least one file input."""
    with pytest.raises(PreconditionError):
        validate_job_preconditions(file_inputs=None)


def test_job_accepts_readable_file(tmp_path: Path) -> None:
    """Job preconditions accept readable file inputs."""
    job_file = tmp_path / "job.txt"
    job_file.write_text("job")
    validate_job_preconditions(file_inputs=[job_file])


def test_evaluate_requires_both_paths(tmp_path: Path) -> None:
    """Evaluate preconditions require both profile and job paths."""
    profile_path = tmp_path / "profile.json"
    profile_path.write_text("{}")
    with pytest.raises(PreconditionError):
        validate_evaluate_preconditions(profile_path=profile_path, job_path=None)


def test_evaluate_rejects_unreadable_inputs(tmp_path: Path) -> None:
    """Evaluate preconditions reject unreadable inputs."""
    profile_path = tmp_path / "profile.json"
    profile_path.write_text("{}")
    missing = tmp_path / "missing.json"
    with pytest.raises(PreconditionError):
        validate_evaluate_preconditions(profile_path=profile_path, job_path=missing)


def test_evaluate_accepts_readable_inputs(tmp_path: Path) -> None:
    """Evaluate preconditions accept readable profile and job inputs."""
    profile_path = tmp_path / "profile.json"
    job_path = tmp_path / "job.json"
    profile_path.write_text("{}")
    job_path.write_text("{}")
    validate_evaluate_preconditions(profile_path=profile_path, job_path=job_path)
