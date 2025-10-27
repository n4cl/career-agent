from __future__ import annotations

import pytest

from profile_agent.session.builder import build_session


def test_build_session_provides_default_profile_path() -> None:
    """貼り付けテキストだけでセッション辞書を構築する基本ケースを検証する。"""
    result = build_session(text_inputs=["自己紹介", "職務経歴"])

    assert result["text_inputs"] == ["自己紹介", "職務経歴"]
    assert result["profile_path"] == "profiles/user_profile.json"
    assert result["interactive"] is True
    assert result.get("force_overwrite") is False


def test_build_session_accepts_optional_overrides() -> None:
    """対話モード無効やターゲット指定など追加オプションを受け取れることを確認する。"""
    result = build_session(
        text_inputs=["更新用テキスト"],
        profile_path="profiles/custom.json",
        interactive=False,
        force_overwrite=True,
        target_fields=["summary", "skills"],
    )

    assert result["profile_path"] == "profiles/custom.json"
    assert result["interactive"] is False
    assert result["force_overwrite"] is True
    assert result["target_fields"] == ["summary", "skills"]


def test_build_session_requires_non_empty_text_inputs() -> None:
    """テキスト入力が無い場合はエラーとして扱う。"""
    with pytest.raises(ValueError):
        build_session(text_inputs=[])
