"""成果物の保存形式を検証する。"""

from __future__ import annotations

import json
from pathlib import Path

from agent_core.artifact_writer import save_json_artifact


def test_artifact_writer_saves_human_readable_utf8(tmp_path: Path) -> None:
    """人間可読な UTF-8 形式で保存される。"""
    target = tmp_path / "profile.json"
    payload = {"name": "太郎", "score": 10}

    save_json_artifact(
        payload=payload,
        path=target,
        allow_overwrite=False,
        create_dirs=True,
        make_backup=False,
    )

    text = target.read_text(encoding="utf-8")
    assert "太郎" in text
    assert "\n" in text
    assert json.loads(text) == payload
