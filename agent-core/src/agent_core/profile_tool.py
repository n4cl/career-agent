"""プロフィール構造化ツール."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Mapping

from .artifact_writer import save_json_artifact

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


@dataclass(frozen=True)
class ProfileResult(ProfileDraft):
    """確定済みプロフィール結果."""

    status: Literal["incomplete", "complete"]
    missing: list[str]


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

    def __init__(
        self,
        *,
        output_path: Path | None = None,
        allow_overwrite: bool = True,
        create_dirs: bool = True,
        make_backup: bool = True,
    ) -> None:
        self._output_path = output_path or Path("profiles/profile.json")
        self._allow_overwrite = allow_overwrite
        self._create_dirs = create_dirs
        self._make_backup = make_backup

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

    def finalize(self, draft: ProfileDraft) -> ProfileResult:
        """ドラフトを保存して完了判定を返す。"""
        missing = _detect_missing(draft)
        status: Literal["incomplete", "complete"] = (
            "complete" if not missing else "incomplete"
        )
        result = ProfileResult(
            metadata=draft.metadata,
            summary=draft.summary,
            career=list(draft.career),
            plan=list(draft.plan),
            age_band=draft.age_band,
            prefecture=draft.prefecture,
            certifications=list(draft.certifications),
            status=status,
            missing=missing,
        )
        payload = _to_payload(result)
        save_json_artifact(
            payload=payload,
            path=self._output_path,
            allow_overwrite=self._allow_overwrite,
            create_dirs=self._create_dirs,
            make_backup=self._make_backup,
        )
        return result


def _detect_missing(draft: ProfileDraft) -> list[str]:
    """欠損項目を検出する。"""
    missing: list[str] = []
    if not draft.summary.strip():
        missing.append("summary")
    if not any(item.strip() for item in draft.career):
        missing.append("career")
    return missing


def _to_payload(result: ProfileResult) -> dict[str, Any]:
    """保存用の辞書を生成する。"""
    return {
        "metadata": result.metadata,
        "summary": result.summary,
        "career": list(result.career),
        "plan": list(result.plan),
        "age_band": result.age_band,
        "prefecture": result.prefecture,
        "certifications": list(result.certifications),
        "status": result.status,
        "missing": list(result.missing),
    }
