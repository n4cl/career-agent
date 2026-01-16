"""成果物を人間可読な形式で保存する。"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any
import json

from .storage import FileStorage, SaveResult


def _serialize_json(payload: Mapping[str, Any]) -> str:
    """成果物を可読な JSON 文字列に変換する。"""
    return json.dumps(payload, ensure_ascii=False, indent=2)


def save_json_artifact(
    *,
    payload: Mapping[str, Any],
    path: Path,
    allow_overwrite: bool,
    create_dirs: bool,
    make_backup: bool,
    storage: FileStorage | None = None,
) -> SaveResult:
    """JSON 成果物を UTF-8 で保存する。"""
    writer = storage or FileStorage()
    serialized = _serialize_json(payload)
    return writer.save_text(
        path=path,
        content=serialized,
        allow_overwrite=allow_overwrite,
        create_dirs=create_dirs,
        make_backup=make_backup,
    )
