"""Environment sanity checks for agent-core."""

from __future__ import annotations

from pathlib import Path

import tomllib


def _parse_min_version(spec: str) -> tuple[int, int]:
    """Extract the minimum major/minor version from a requires-python spec."""
    first = spec.split(",", 1)[0].strip()
    if not first.startswith(">="):
        raise ValueError(f"Unsupported requires-python spec: {spec}")
    version_text = first.removeprefix(">=").strip()
    parts = version_text.split(".")
    if len(parts) < 2:
        raise ValueError(f"Invalid version format: {version_text}")
    return int(parts[0]), int(parts[1])


def test_requires_python_is_314_or_higher() -> None:
    """Ensure requires-python is set to >=3.14 in pyproject."""
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text())
    requires = data["project"]["requires-python"]
    assert _parse_min_version(requires) >= (3, 14)
