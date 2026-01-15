"""プロンプト定義を検証する。"""

from __future__ import annotations

from agent_core.prompts import profile_question


def test_profile_question_returns_known_prompt() -> None:
    """既知のフィールドは定義済み文言を返す。"""
    assert profile_question("summary") == "summary を教えてください。"


def test_profile_question_falls_back_to_default() -> None:
    """未知のフィールドはデフォルト文言を返す。"""
    assert profile_question("unknown") == "unknown を教えてください。"
