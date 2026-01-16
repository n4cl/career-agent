"""会話ブロックの管理."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from .log_writer import LogRecord

Role = Literal["user", "agent"]


@dataclass(frozen=True)
class ConversationBlock:
    """会話ブロックを表すデータ構造。"""

    role: Role
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


def _validate_role(role: str) -> Role:
    """許可された役割のみを受け付ける。"""
    if role not in {"user", "agent"}:
        raise ValueError(f"unsupported role: {role}")
    return role  # type: ignore[return-value]


class ConversationStore:
    """会話ブロックを順序付きで保持する。"""

    def __init__(self) -> None:
        self._blocks: list[ConversationBlock] = []

    def append(
        self,
        *,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """会話ブロックを末尾に追加する。"""
        normalized_role = _validate_role(role)
        self._blocks.append(
            ConversationBlock(
                role=normalized_role,
                content=content,
                metadata=dict(metadata or {}),
            )
        )

    def list(self) -> list[ConversationBlock]:
        """保持している会話ブロックを返す。"""
        return list(self._blocks)


def build_log_record(store: ConversationStore, *, run_id: str) -> LogRecord:
    """会話履歴をログレコードに変換する。"""
    blocks = store.list()
    questions = [block.content for block in blocks if block.role == "agent"]
    input_refs = [block.content for block in blocks if block.role == "user"]
    conversation = [
        {"role": block.role, "content": block.content, "metadata": dict(block.metadata)}
        for block in blocks
    ]
    return LogRecord(
        questions=questions,
        warnings=[],
        input_refs=input_refs,
        metadata={"run_id": run_id, "conversation": conversation},
    )
