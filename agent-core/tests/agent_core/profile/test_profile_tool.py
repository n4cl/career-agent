"""プロフィール構造化ツールを検証する。"""

from __future__ import annotations

from dataclasses import dataclass

from agent_core.shared.context import ExecutionContext
from agent_core.profile.profile_tool import ProfileToolImpl


def test_profile_tool_builds_structured_profile_from_payload() -> None:
    """メタデータ/要約/経歴/プランを持つ構造を生成する。"""
    context = ExecutionContext(
        mode="profile",
        text_inputs=[],
        file_inputs=[],
        options={
            "profile_payload": {
                "metadata": {"source": "input"},
                "summary": "summary",
                "career": ["career"],
                "plan": ["plan"],
                "age_band": "30代",
                "prefecture": "東京都",
                "certifications": ["AWS SAA"],
            }
        },
    )

    tool = ProfileToolImpl()
    draft = tool.build(context)

    assert draft.metadata == {"source": "input"}
    assert draft.summary == "summary"
    assert draft.career == ["career"]
    assert draft.plan == ["plan"]
    assert draft.age_band == "30代"
    assert draft.prefecture == "東京都"
    assert draft.certifications == ["AWS SAA"]


def test_profile_tool_uses_text_inputs_when_payload_missing() -> None:
    """入力が無い場合はテキスト入力から要約を構築する。"""
    context = ExecutionContext(
        mode="profile",
        text_inputs=["hello", "world"],
        file_inputs=[],
        options={},
    )

    tool = ProfileToolImpl()
    draft = tool.build(context)

    assert draft.summary == "hello world"
    assert draft.metadata == {}
    assert draft.career == []
    assert draft.plan == []
    assert draft.age_band == ""
    assert draft.prefecture == ""
    assert draft.certifications == []


def test_profile_tool_treats_conversion_failures_as_empty() -> None:
    """型変換に失敗した値は空として扱う。"""

    @dataclass
    class BadStr:
        """文字列化が失敗する値."""

        def __str__(self) -> str:
            raise ValueError("broken")

    context = ExecutionContext(
        mode="profile",
        text_inputs=[],
        file_inputs=[],
        options={
            "profile_payload": {
                "metadata": {"key": BadStr()},
                "summary": BadStr(),
                "career": [BadStr()],
                "plan": [BadStr()],
                "age_band": BadStr(),
                "prefecture": BadStr(),
                "certifications": [BadStr()],
            }
        },
    )

    tool = ProfileToolImpl()
    draft = tool.build(context)

    assert draft.metadata == {"key": ""}
    assert draft.summary == ""
    assert draft.career == [""]
    assert draft.plan == [""]
    assert draft.age_band == ""
    assert draft.prefecture == ""
    assert draft.certifications == [""]
