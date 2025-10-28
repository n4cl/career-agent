"""プロフィールスキーマ定義とドラフト/最終バリデーション."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


@dataclass(slots=True)
class ProfileMetadata:
    """プロフィールの基本情報."""

    name: str
    birth_year: int | None = None
    experience_years: int | None = None
    location: str | None = None
    last_updated: str | None = None


@dataclass(slots=True)
class ProfileSummary:
    """要約情報."""

    headline: str
    summary: str
    strengths: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    certifications: list[str] = field(default_factory=list)


@dataclass(slots=True)
class CareerEntry:
    """職務経歴の 1 エントリ."""

    company: str
    role: str
    start_date: str | None = None
    end_date: str | None = None
    achievements: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ProfilePlan:
    """キャリアの希望や避けたい条件."""

    wants_to_do: str | None = None
    interests: list[str] | None = None
    preferences: Mapping[str, Any] | None = None
    avoid: Mapping[str, Any] | None = None


@dataclass(slots=True)
class Profile:
    """プロフィール全体のスキーマ."""

    metadata: ProfileMetadata
    summary: ProfileSummary
    career: list[CareerEntry]
    plan: ProfilePlan | None = None


@dataclass(slots=True)
class ProfileDraft:
    """プロフィール生成途中のドラフト."""

    profile: Profile
    missing_fields: list[str]

    def is_complete(self) -> bool:
        """欠損項目が無いかを判定する。"""
        return not self.missing_fields


class ProfileValidationError(ValueError):
    """プロフィール確定時の未充足エラー."""

    def __init__(self, missing_fields: Sequence[str]):
        fields = sorted(set(missing_fields))
        super().__init__(f"missing required fields: {', '.join(fields)}")
        self.missing_fields = fields


def parse_profile(data: Mapping[str, Any]) -> ProfileDraft:
    """辞書データからドラフトを構築し、欠損項目を収集する。"""
    metadata_raw, metadata_missing = _require_mapping(data.get("metadata"), "metadata")
    summary_raw, summary_missing = _require_mapping(data.get("summary"), "summary")
    career_raw = data.get("career")

    metadata, metadata_errors = _build_metadata(metadata_raw)
    summary, summary_errors = _build_summary(summary_raw)
    career, career_errors = _build_career(career_raw)
    plan = _build_plan(data.get("plan"))

    profile = Profile(metadata=metadata, summary=summary, career=career, plan=plan)
    missing = sorted(
        set(
            metadata_missing
            + summary_missing
            + metadata_errors
            + summary_errors
            + career_errors
            + detect_missing_fields(profile)
        )
    )

    return ProfileDraft(profile=profile, missing_fields=missing)


def finalize_profile(draft: ProfileDraft) -> Profile:
    """ドラフトを検証し、未充足があればエラーを出して確定させる。"""
    missing = detect_missing_fields(draft.profile)
    if missing:
        raise ProfileValidationError(missing)
    return draft.profile


def detect_missing_fields(profile: Profile) -> list[str]:
    """プロフィール内の必須欠損を列挙する。"""
    missing: list[str] = []

    if not profile.metadata.name.strip():
        missing.append("metadata.name")

    if not profile.summary.headline.strip():
        missing.append("summary.headline")
    if not profile.summary.summary.strip():
        missing.append("summary.summary")

    if not profile.career:
        missing.append("career")
    else:
        for idx, entry in enumerate(profile.career):
            if not entry.company.strip():
                missing.append(f"career[{idx}].company")
            if not entry.role.strip():
                missing.append(f"career[{idx}].role")

    return sorted(set(missing))


def _require_mapping(
    value: Any,
    field_name: str,
) -> tuple[Mapping[str, Any], list[str]]:
    if not isinstance(value, Mapping):
        return {}, [field_name]
    return value, []


def _build_metadata(
    metadata_raw: Mapping[str, Any],
) -> tuple[ProfileMetadata, list[str]]:
    missing: list[str] = []
    name = metadata_raw.get("name")
    if not name:
        missing.append("metadata.name")

    return ProfileMetadata(
        name=_coerce_str(name) or "",
        birth_year=_coerce_int(metadata_raw.get("birth_year")),
        experience_years=_coerce_int(metadata_raw.get("experience_years")),
        location=_coerce_str(metadata_raw.get("location")),
        last_updated=_coerce_str(metadata_raw.get("last_updated")),
    ), missing


def _build_summary(
    summary_raw: Mapping[str, Any],
) -> tuple[ProfileSummary, list[str]]:
    missing: list[str] = []
    headline = summary_raw.get("headline")
    summary_text = summary_raw.get("summary")

    if not headline:
        missing.append("summary.headline")
    if not summary_text:
        missing.append("summary.summary")

    return ProfileSummary(
        headline=_coerce_str(headline) or "",
        summary=_coerce_str(summary_text) or "",
        strengths=_ensure_str_list(summary_raw.get("strengths")),
        skills=_ensure_str_list(summary_raw.get("skills")),
        certifications=_ensure_str_list(summary_raw.get("certifications")),
    ), missing


def _build_career(
    career_raw: Any,
    field_name: str = "career",
) -> tuple[list[CareerEntry], list[str]]:
    if career_raw is None:
        return [], [field_name]
    if not isinstance(career_raw, Sequence) or isinstance(career_raw, (str, bytes)):
        return [], [field_name]

    entries: list[CareerEntry] = []
    missing: list[str] = []
    for idx, item in enumerate(career_raw):
        if not isinstance(item, Mapping):
            missing.append(f"career[{idx}]")
            continue

        company = item.get("company")
        role = item.get("role")
        if not company:
            missing.append(f"career[{idx}].company")
        if not role:
            missing.append(f"career[{idx}].role")

        entries.append(
            CareerEntry(
                company=_coerce_str(company) or "",
                role=_coerce_str(role) or "",
                start_date=_coerce_str(item.get("start_date")),
                end_date=_coerce_str(item.get("end_date")),
                achievements=_ensure_str_list(item.get("achievements")),
            )
        )

    if not entries:
        missing.append("career")

    return entries, missing


def _build_plan(plan_raw: Any) -> ProfilePlan | None:
    if plan_raw is None:
        return None
    if not isinstance(plan_raw, Mapping):
        return ProfilePlan()

    return ProfilePlan(
        wants_to_do=_coerce_str(plan_raw.get("wants_to_do")),
        interests=_ensure_str_list(plan_raw.get("interests")) or None,
        preferences=plan_raw.get("preferences")
        if isinstance(plan_raw.get("preferences"), Mapping)
        else None,
        avoid=plan_raw.get("avoid") if isinstance(plan_raw.get("avoid"), Mapping) else None,
    )


def _coerce_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _coerce_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, bytes):
        return value.decode()
    return str(value)


def _ensure_str_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, (str, bytes)):
        coerced = _coerce_str(value)
        return [coerced] if coerced else []
    if isinstance(value, Sequence):
        result: list[str] = []
        for item in value:
            coerced = _coerce_str(item)
            if coerced:
                result.append(coerced)
        return result
    return []
