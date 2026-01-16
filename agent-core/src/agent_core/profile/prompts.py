"""プロンプト定義を集約する。"""

from __future__ import annotations

PROFILE_QUESTIONS: dict[str, str] = {
    "summary": "summary を教えてください。",
    "career": "career を教えてください。",
}


def profile_question(field: str) -> str:
    """プロフィールの質問文を返す。"""
    return PROFILE_QUESTIONS.get(field, f"{field} を教えてください。")
