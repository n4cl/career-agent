"""プロフィール対話CLIを検証する。"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from agent_core.cli.app import app


def test_profile_interview_non_interactive_saves_incomplete(tmp_path: Path) -> None:
    """非対話モードは未完了として保存する。"""
    runner = CliRunner()
    output_path = tmp_path / "profile.json"

    result = runner.invoke(
        app,
        [
            "profile",
            "interview",
            "--output",
            str(output_path),
            "--non-interactive",
        ],
    )

    assert result.exit_code == 0
    assert "状態: incomplete" in result.output
    assert "欠損: career" in result.output
    assert f"保存先: {output_path}" in result.output
    saved = json.loads(output_path.read_text(encoding="utf-8"))
    assert saved["status"] == "incomplete"
    assert saved["missing"] == ["career"]


def test_profile_interview_interactive_completes(tmp_path: Path) -> None:
    """対話モードで回答すると完了となる。"""
    runner = CliRunner()
    output_path = tmp_path / "profile.json"

    result = runner.invoke(
        app,
        [
            "profile",
            "interview",
            "--output",
            str(output_path),
            "--max-attempts",
            "2",
        ],
        input="backend\n",
    )

    assert result.exit_code == 0
    assert "状態: complete" in result.output
    assert "欠損: なし" in result.output
    assert f"保存先: {output_path}" in result.output
    saved = json.loads(output_path.read_text(encoding="utf-8"))
    assert saved["status"] == "complete"
    assert saved["career"] == ["backend"]
