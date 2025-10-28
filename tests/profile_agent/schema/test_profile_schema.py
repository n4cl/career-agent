from __future__ import annotations

import pytest

from profile_agent.schema.profile import (
    CareerEntry,
    Profile,
    ProfileMetadata,
    ProfilePlan,
    ProfileSummary,
    load_profile,
)


def test_load_profile_returns_profile_dataclass() -> None:
    """辞書入力が適切に Profile データクラスへ変換されることを確認する。"""
    raw = {
        "metadata": {
            "name": "山田太郎",
            "last_updated": "2025-10-27",
            "experience_years": 8,
        },
        "summary": {
            "headline": "バックエンドエンジニア",
            "summary": "SaaS 企業で API 開発を担当。",
            "strengths": ["アーキテクチャ設計"],
            "skills": ["Python", "FastAPI"],
        },
        "career": [
            {
                "company": "Acme Inc.",
                "role": "Backend Engineer",
                "start_date": "2020-01",
                "end_date": None,
                "achievements": ["REST API のリファクタリング"],
            }
        ],
        "plan": {
            "wants_to_do": "テックリードとして改善活動を推進",
            "interests": ["分散システム"],
        },
    }

    profile = load_profile(raw)

    assert isinstance(profile, Profile)
    assert profile.metadata == ProfileMetadata(
        name="山田太郎",
        last_updated="2025-10-27",
        experience_years=8,
    )
    assert profile.summary == ProfileSummary(
        headline="バックエンドエンジニア",
        summary="SaaS 企業で API 開発を担当。",
        strengths=["アーキテクチャ設計"],
        skills=["Python", "FastAPI"],
        certifications=[],
    )
    assert profile.career == [
        CareerEntry(
            company="Acme Inc.",
            role="Backend Engineer",
            start_date="2020-01",
            end_date=None,
            achievements=["REST API のリファクタリング"],
        )
    ]
    assert profile.plan == ProfilePlan(
        wants_to_do="テックリードとして改善活動を推進",
        interests=["分散システム"],
        preferences=None,
        avoid=None,
    )


def test_load_profile_requires_core_fields() -> None:
    """必須フィールドが欠けている場合は ValueError を送出する。"""
    raw = {
        "metadata": {},
        "summary": {"headline": "headline"},
        "career": [],
    }

    with pytest.raises(ValueError) as excinfo:
        load_profile(raw)

    message = str(excinfo.value)
    assert "metadata.name" in message
    assert "summary.summary" in message


def test_load_profile_validates_career_entries() -> None:
    """キャリア項目に必須情報が欠けている場合はエラーとなる。"""
    raw = {
        "metadata": {"name": "山田太郎"},
        "summary": {"headline": "headline", "summary": "summary"},
        "career": [
            {"company": "Example"},  # role が欠けている
        ],
    }

    with pytest.raises(ValueError) as excinfo:
        load_profile(raw)

    assert "career[0].role" in str(excinfo.value)
