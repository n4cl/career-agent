"""セッション辞書構築用のヘルパー."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

DEFAULT_PROFILE_PATH = "profiles/user_profile.json"


def _normalize_text_inputs(text_inputs: Sequence[str] | None) -> list[str]:
    """空要素を除去しつつテキスト入力を正規化する."""
    if not text_inputs:
        raise ValueError("text_inputs must not be empty")

    normalized = [text for text in text_inputs if text and text.strip()]
    if not normalized:
        raise ValueError("text_inputs must contain non-empty values")

    return list(normalized)


def build_session(
    *,
    text_inputs: Sequence[str] | None,
    profile_path: str | None = None,
    interactive: bool = True,
    force_overwrite: bool = False,
    target_fields: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Profile Agent の CLI から渡すセッション辞書を組み立てる."""
    normalized_inputs = _normalize_text_inputs(text_inputs)

    session: dict[str, Any] = {
        "profile_path": profile_path or DEFAULT_PROFILE_PATH,
        "text_inputs": normalized_inputs,
        "interactive": interactive,
        "force_overwrite": force_overwrite,
    }

    if target_fields:
        session["target_fields"] = list(target_fields)

    return session
