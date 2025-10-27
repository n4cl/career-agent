from __future__ import annotations

import pytest

from profile_agent.workflow.nodes.collect_input import collect_input_node
from profile_agent.workflow.state import ProfileState


def test_collect_input_from_pasted_chunks_only() -> None:
    """貼り付け入力だけをチャンク化し、連番 ID を付与する。"""
    node = collect_input_node()
    state = ProfileState(
        mode="create",
        session={
            "profile_path": "profiles/user_profile.json",
            "text_inputs": ["自己紹介", "職務経歴"],
        },
    )

    result = node(state)

    assert result.session["input_chunks"] == [
        {"id": 0, "source": "text", "content": "自己紹介"},
        {"id": 1, "source": "text", "content": "職務経歴"},
    ]


def test_collect_input_preserves_existing_chunks() -> None:
    """既存の input_chunks があれば上書きせずにスキップする。"""
    node = collect_input_node()
    state = ProfileState(
        mode="create",
        session={
            "profile_path": "profiles/user_profile.json",
            "text_inputs": ["自己紹介"],
            "input_chunks": [{"id": 99, "source": "text", "content": "既存"}],
        },
    )

    result = node(state)

    assert result.session["input_chunks"][0]["id"] == 99


def test_collect_input_requires_text_inputs() -> None:
    """CLI テキスト入力がない場合は ValueError を送出する。"""
    node = collect_input_node()
    state = ProfileState(
        mode="create",
        session={"profile_path": "profiles/user_profile.json"},
    )

    with pytest.raises(ValueError):
        node(state)
