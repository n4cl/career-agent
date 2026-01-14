"""プロフィール構造化ツール."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .context import ExecutionContext


@dataclass(frozen=True)
class ProfileDraft:
    """構造化されたプロフィールのドラフト."""

    metadata: dict[str, str]
    summary: str
    career: list[str]
    plan: list[str]
    age_band: str
    prefecture: str
    certifications: list[str]


def _coerce_str(value: object) -> str:
    """値を文字列に変換し、失敗時は空を返す。"""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        return str(value)
    except (TypeError, ValueError):
        # 型変換エラーは空として扱う方針
        return ""


def _coerce_str_list(value: object) -> list[str]:
    """リストを文字列リストに変換する。"""
    if not isinstance(value, list):
        return []
    return [_coerce_str(item) for item in value]


def _coerce_metadata(value: object) -> dict[str, str]:
    """メタデータを辞書として正規化する。"""
    if not isinstance(value, Mapping):
        return {}
    normalized: dict[str, str] = {}
    for key, item in value.items():
        key_str = _coerce_str(key)
        if not key_str:
            continue
        normalized[key_str] = _coerce_str(item)
    return normalized


def _build_draft_from_payload(payload: Mapping[str, Any]) -> ProfileDraft:
    """ペイロードからプロフィールを構造化する。"""
    return ProfileDraft(
        metadata=_coerce_metadata(payload.get("metadata")),
        summary=_coerce_str(payload.get("summary")),
        career=_coerce_str_list(payload.get("career")),
        plan=_coerce_str_list(payload.get("plan")),
        age_band=_coerce_str(payload.get("age_band")),
        prefecture=_coerce_str(payload.get("prefecture")),
        certifications=_coerce_str_list(payload.get("certifications")),
    )


class ProfileToolImpl:
    """プロフィール構造化の実装."""

    def build(self, context: ExecutionContext) -> ProfileDraft:
        """プロフィールドラフトを構築する。"""
        if context.mode != "profile":
            raise ValueError("profile context is required")

        payload = context.options.get("profile_payload")
        if isinstance(payload, Mapping):
            return _build_draft_from_payload(payload)

        summary = " ".join(context.text_inputs).strip()
        return ProfileDraft(
            metadata={},
            summary=summary,
            career=[],
            plan=[],
            age_band="",
            prefecture="",
            certifications=[],
        )
