"""プロフィール構造化ツール."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Mapping

from ..shared.artifact_writer import save_json_artifact
from ..shared.context import ExecutionContext


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
    warnings: list[str] = field(default_factory=list)


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
        missing = detect_missing(draft)
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
            warnings=[],
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

    def update(self, context: ExecutionContext) -> ProfileResult:
        """既存プロフィールを読み込み、指定範囲を更新する。"""
        if context.mode != "profile":
            raise ValueError("profile context is required")

        if not self._output_path.exists():
            raise ValueError("profile not found")

        payload = json.loads(self._output_path.read_text(encoding="utf-8"))
        base = _from_payload(payload)
        update_targets = context.options.get("update_targets") or []
        if not isinstance(update_targets, list):
            update_targets = []

        updates = context.options.get("profile_payload") or {}
        if not isinstance(updates, Mapping):
            updates = {}

        updated, warnings = _merge_profile(base, updates, update_targets)
        result = ProfileResult(
            metadata=updated.metadata,
            summary=updated.summary,
            career=list(updated.career),
            plan=list(updated.plan),
            age_band=updated.age_band,
            prefecture=updated.prefecture,
            certifications=list(updated.certifications),
            status=updated.status,
            missing=list(updated.missing),
            warnings=warnings,
        )
        payload = _to_payload(result)
        save_json_artifact(
            payload=payload,
            path=self._output_path,
            allow_overwrite=True,
            create_dirs=self._create_dirs,
            make_backup=self._make_backup,
        )
        return result


def detect_missing(draft: ProfileDraft) -> list[str]:
    """欠損項目を検出する。"""
    missing: list[str] = []
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
        "warnings": list(result.warnings),
    }


def _from_payload(payload: Mapping[str, Any]) -> ProfileResult:
    """保存データからプロフィール結果を構築する。"""
    draft = _build_draft_from_payload(payload)
    status = payload.get("status")
    if status not in {"complete", "incomplete"}:
        status = "incomplete"
    missing = payload.get("missing")
    if not isinstance(missing, list):
        missing = []
    warnings = payload.get("warnings")
    if not isinstance(warnings, list):
        warnings = []
    return ProfileResult(
        metadata=draft.metadata,
        summary=draft.summary,
        career=list(draft.career),
        plan=list(draft.plan),
        age_band=draft.age_band,
        prefecture=draft.prefecture,
        certifications=list(draft.certifications),
        status=status,
        missing=[_coerce_str(item) for item in missing],
        warnings=[_coerce_str(item) for item in warnings],
    )


def _merge_profile(
    base: ProfileResult,
    updates: Mapping[str, Any],
    update_targets: list[str],
) -> tuple[ProfileResult, list[str]]:
    """指定範囲だけ更新したプロフィールを返す。"""
    warnings: list[str] = []
    allowed = {
        "metadata",
        "summary",
        "career",
        "plan",
        "age_band",
        "prefecture",
        "certifications",
    }
    targets = [_coerce_str(item) for item in update_targets]
    normalized_targets = [item for item in targets if item]
    for item in normalized_targets:
        if item not in allowed:
            warnings.append(item)

    def should_update(field: str) -> bool:
        return field in normalized_targets

    metadata = base.metadata
    if should_update("metadata"):
        metadata = _coerce_metadata(updates.get("metadata"))

    summary = base.summary
    if should_update("summary"):
        summary = _coerce_str(updates.get("summary"))

    career = base.career
    if should_update("career"):
        career = _coerce_str_list(updates.get("career"))

    plan = base.plan
    if should_update("plan"):
        plan = _coerce_str_list(updates.get("plan"))

    age_band = base.age_band
    if should_update("age_band"):
        age_band = _coerce_str(updates.get("age_band"))

    prefecture = base.prefecture
    if should_update("prefecture"):
        prefecture = _coerce_str(updates.get("prefecture"))

    certifications = base.certifications
    if should_update("certifications"):
        certifications = _coerce_str_list(updates.get("certifications"))

    updated = ProfileDraft(
        metadata=metadata,
        summary=summary,
        career=list(career),
        plan=list(plan),
        age_band=age_band,
        prefecture=prefecture,
        certifications=list(certifications),
    )
    missing = detect_missing(updated)
    status: Literal["incomplete", "complete"] = (
        "complete" if not missing else "incomplete"
    )
    return (
        ProfileResult(
            metadata=metadata,
            summary=summary,
            career=list(career),
            plan=list(plan),
            age_band=age_band,
            prefecture=prefecture,
            certifications=list(certifications),
            status=status,
            missing=missing,
            warnings=warnings,
        ),
        warnings,
    )
