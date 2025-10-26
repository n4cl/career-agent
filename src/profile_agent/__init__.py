"""profile_agent パッケージの公開インターフェース."""

from __future__ import annotations

from importlib import metadata


def _resolve_version() -> str:
    """パッケージメタデータからバージョンを取得する."""
    try:
        return metadata.version("career-agent")
    except metadata.PackageNotFoundError:
        return "0.0.0"


__version__ = _resolve_version()

__all__ = ["__version__"]
