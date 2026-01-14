"""プロフィールの欠損判定と保存を検証する。"""

from __future__ import annotations

import json
from pathlib import Path

from agent_core.profile_tool import ProfileDraft, ProfileToolImpl


def test_finalize_marks_incomplete_when_summary_missing(tmp_path: Path) -> None:
    """要約が欠ける場合は未完了として保存する。"""
    draft = ProfileDraft(
        metadata={},
        summary="",
        career=["backend"],
        plan=[],
        age_band="",
        prefecture="",
        certifications=[],
    )

    tool = ProfileToolImpl(output_path=tmp_path / "profile.json")
    result = tool.finalize(draft)

    assert result.status == "incomplete"
    assert result.missing == ["summary"]
    saved = json.loads((tmp_path / "profile.json").read_text(encoding="utf-8"))
    assert saved["status"] == "incomplete"
    assert saved["missing"] == ["summary"]


def test_finalize_marks_incomplete_when_career_missing(tmp_path: Path) -> None:
    """経歴が無い場合は未完了として保存する。"""
    draft = ProfileDraft(
        metadata={},
        summary="summary",
        career=[],
        plan=[],
        age_band="",
        prefecture="",
        certifications=[],
    )

    tool = ProfileToolImpl(output_path=tmp_path / "profile.json")
    result = tool.finalize(draft)

    assert result.status == "incomplete"
    assert result.missing == ["career"]


def test_finalize_marks_complete_when_required_fields_present(
    tmp_path: Path,
) -> None:
    """要約と経歴が揃う場合は完了として保存する。"""
    draft = ProfileDraft(
        metadata={"source": "input"},
        summary="summary",
        career=["backend"],
        plan=["plan"],
        age_band="30代",
        prefecture="東京都",
        certifications=["AWS SAA"],
    )

    tool = ProfileToolImpl(output_path=tmp_path / "profile.json")
    result = tool.finalize(draft)

    assert result.status == "complete"
    assert result.missing == []
    saved = json.loads((tmp_path / "profile.json").read_text(encoding="utf-8"))
    assert saved["status"] == "complete"
    assert saved["missing"] == []
