from __future__ import annotations

import pytest

from profile_agent.schema.profile import (
    ProfileDraft,
    ProfileValidationError,
    detect_missing_fields,
    finalize_profile,
    parse_profile,
    ProfilePlan,
)


def test_parse_profile_returns_complete_draft() -> None:
    """必須項目が揃っているときは欠損が空のドラフトを返す。"""
    raw = {
        "metadata": {
            "name": "山田太郎",
            "last_updated": "2025-10-27",
        },
        "summary": {
            "headline": "バックエンドエンジニア",
            "summary": "SaaS 企業で API 開発を担当。",
        },
        "career": [
            {"company": "Acme", "role": "Backend Engineer"},
        ],
        "plan": {"wants_to_do": "テックリードを目指す"},
    }

    draft = parse_profile(raw)

    assert isinstance(draft, ProfileDraft)
    assert draft.is_complete()
    assert draft.profile.metadata.name == "山田太郎"
    assert draft.profile.summary.headline == "バックエンドエンジニア"
    assert draft.profile.career[0].company == "Acme"
    assert isinstance(draft.profile.plan, ProfilePlan)


def test_parse_profile_collects_missing_fields_without_exception() -> None:
    """欠損があっても例外にならず、missing_fields に記録される。"""
    raw = {
        "metadata": {},
        "summary": {"headline": "", "summary": ""},
        "career": [],
    }

    draft = parse_profile(raw)

    assert sorted(draft.missing_fields) == [
        "career",
        "metadata.name",
        "summary.headline",
        "summary.summary",
    ]


def test_finalize_profile_raises_when_missing_fields_exist() -> None:
    """欠損が残っているドラフトは finalize でエラーになる。"""
    draft = parse_profile(
        {
            "metadata": {"name": ""},
            "summary": {"headline": "headline", "summary": ""},
            "career": [{"company": "Acme", "role": ""}],
        }
    )

    with pytest.raises(ProfileValidationError) as excinfo:
        finalize_profile(draft)

    assert "metadata.name" in excinfo.value.missing_fields
    assert "summary.summary" in excinfo.value.missing_fields
    assert "career[0].role" in excinfo.value.missing_fields


def test_detect_missing_fields_after_updates() -> None:
    """ドラフトに追記後、欠損検出を再計算して解消できる。"""
    draft = parse_profile(
        {
            "metadata": {"name": ""},
            "summary": {"headline": "headline", "summary": ""},
            "career": [{"company": "", "role": "Engineer"}],
        }
    )

    draft.profile.metadata.name = "山田太郎"
    draft.profile.summary.summary = "自己紹介"
    draft.profile.career[0].company = "Acme"

    missing = detect_missing_fields(draft.profile)

    assert missing == []
    # finalize も成功することを確認
    completed = finalize_profile(
        ProfileDraft(profile=draft.profile, missing_fields=missing)
    )
    assert completed.metadata.name == "山田太郎"
