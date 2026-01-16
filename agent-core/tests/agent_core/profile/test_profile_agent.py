"""プロフィール対話エージェントを検証する。"""

from __future__ import annotations

import json
from pathlib import Path

from agent_core.shared.context import ExecutionContext
from agent_core.shared.conversation import ConversationStore
from agent_core.profile.profile_agent import ProfileAgentImpl
from agent_core.profile.profile_tool import ProfileToolImpl


def test_profile_agent_starts_interview_on_empty_input(tmp_path: Path) -> None:
    """空入力でも対話を開始し、欠損を記録する。"""
    context = ExecutionContext(
        mode="profile",
        text_inputs=[],
        file_inputs=[],
        options={},
    )
    store = ConversationStore()
    tool = ProfileToolImpl(output_path=tmp_path / "profile.json")
    agent = ProfileAgentImpl(tool=tool, store=store, max_attempts=1)

    result = agent.run(context, answers={}, stop=True, attempt=1)

    assert result.status == "incomplete"
    assert result.missing == ["career"]
    blocks = store.list()
    assert any(block.role == "agent" for block in blocks)
    saved = json.loads((tmp_path / "profile.json").read_text(encoding="utf-8"))
    assert saved["status"] == "incomplete"


def test_profile_agent_records_answers_and_completes(tmp_path: Path) -> None:
    """回答を記録し、欠損が解消されれば完了となる。"""
    context = ExecutionContext(
        mode="profile",
        text_inputs=[],
        file_inputs=[],
        options={},
    )
    store = ConversationStore()
    tool = ProfileToolImpl(output_path=tmp_path / "profile.json")
    agent = ProfileAgentImpl(tool=tool, store=store, max_attempts=2)

    result = agent.run(
        context,
        answers={"summary": "summary", "career": ["backend"]},
        stop=False,
        attempt=1,
    )

    assert result.status == "complete"
    assert result.missing == []
    roles = [block.role for block in store.list()]
    assert "agent" in roles
    assert "user" in roles


def test_profile_agent_re_evaluates_missing_after_partial_answer(
    tmp_path: Path,
) -> None:
    """部分回答後に欠損が再評価される。"""
    context = ExecutionContext(
        mode="profile",
        text_inputs=[],
        file_inputs=[],
        options={},
    )
    store = ConversationStore()
    tool = ProfileToolImpl(output_path=tmp_path / "profile.json")
    agent = ProfileAgentImpl(tool=tool, store=store, max_attempts=1)

    result = agent.run(
        context,
        answers={"summary": "summary"},
        stop=True,
        attempt=1,
    )

    assert result.status == "incomplete"
    assert result.missing == ["career"]
