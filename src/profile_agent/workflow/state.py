"""LangGraph 用の共有ステート定義."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

ProfileMode = Literal["create", "update"]


@dataclass
class ProfileState:
    """Profile Agent の LangGraph ステート."""

    mode: ProfileMode
    session: dict[str, Any] = field(default_factory=dict)
    profile: dict[str, Any] | None = None
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if "profile_path" not in self.session:
            raise ValueError("session.profile_path is required")
