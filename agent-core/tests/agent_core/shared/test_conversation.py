"""会話ブロック管理を検証する。"""

from __future__ import annotations

import pytest

from agent_core.shared.conversation import ConversationStore


def test_conversation_store_appends_user_and_agent_blocks() -> None:
    """ユーザー/エージェントの2種類を追加できる。"""
    store = ConversationStore()
    store.append(role="user", content="hello")
    store.append(role="agent", content="hi")
    blocks = store.list()

    assert [block.role for block in blocks] == ["user", "agent"]
    assert [block.content for block in blocks] == ["hello", "hi"]


def test_conversation_store_preserves_order() -> None:
    """追加順を保持する。"""
    store = ConversationStore()
    store.append(role="user", content="first")
    store.append(role="agent", content="second")
    store.append(role="user", content="third")
    assert [block.content for block in store.list()] == ["first", "second", "third"]


def test_conversation_store_allows_optional_metadata() -> None:
    """メタ情報は任意で付与できる。"""
    store = ConversationStore()
    store.append(role="user", content="hi", metadata={"source": "file"})
    block = store.list()[0]
    assert block.metadata == {"source": "file"}


def test_conversation_store_rejects_unknown_role() -> None:
    """許可されていない役割は拒否する。"""
    store = ConversationStore()
    with pytest.raises(ValueError):
        store.append(role="system", content="nope")
