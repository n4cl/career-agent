"""プロフィール更新モードを検証する。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_core.shared.context import ExecutionContext
from agent_core.profile.profile_tool import ProfileToolImpl


def _save_profile(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_update_merges_only_requested_sections(tmp_path: Path) -> None:
    """更新対象のみ差し替え、他は保持する。"""
    profile_path = tmp_path / "profile.json"
    _save_profile(
        profile_path,
        {
            "metadata": {"source": "old"},
            "summary": "old summary",
            "career": ["old career"],
            "plan": ["old plan"],
            "age_band": "30代",
            "prefecture": "東京都",
            "certifications": ["AWS SAA"],
            "status": "complete",
            "missing": [],
        },
    )

    context = ExecutionContext(
        mode="profile",
        text_inputs=[],
        file_inputs=[],
        options={
            "profile_payload": {"summary": "new summary"},
            "update_targets": ["summary"],
        },
    )

    tool = ProfileToolImpl(output_path=profile_path)
    updated = tool.update(context)

    assert updated.summary == "new summary"
    assert updated.career == ["old career"]
    assert updated.plan == ["old plan"]
    assert updated.metadata == {"source": "old"}
    assert updated.certifications == ["AWS SAA"]


def test_update_errors_when_profile_missing(tmp_path: Path) -> None:
    """既存プロフィールが無い場合はエラーとする。"""
    profile_path = tmp_path / "profile.json"
    context = ExecutionContext(
        mode="profile",
        text_inputs=[],
        file_inputs=[],
        options={"update_targets": ["summary"]},
    )

    tool = ProfileToolImpl(output_path=profile_path)

    with pytest.raises(ValueError):
        tool.update(context)


def test_update_warns_on_unknown_targets(tmp_path: Path) -> None:
    """未知の更新対象は警告に記録される。"""
    profile_path = tmp_path / "profile.json"
    _save_profile(
        profile_path,
        {
            "metadata": {},
            "summary": "summary",
            "career": ["career"],
            "plan": [],
            "age_band": "",
            "prefecture": "",
            "certifications": [],
            "status": "complete",
            "missing": [],
        },
    )

    context = ExecutionContext(
        mode="profile",
        text_inputs=[],
        file_inputs=[],
        options={
            "profile_payload": {"summary": "updated"},
            "update_targets": ["unknown", "summary"],
        },
    )

    tool = ProfileToolImpl(output_path=profile_path)
    updated = tool.update(context)

    assert updated.summary == "updated"
    assert "unknown" in updated.warnings
