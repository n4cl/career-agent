"""貼り付け入力のチャンク化ノード."""

from __future__ import annotations

from collections.abc import Callable

from ..state import ProfileState


def collect_input_node() -> Callable[[ProfileState], ProfileState]:
    """貼り付け入力をチャンクに変換する LangGraph ノード."""

    def _runner(state: ProfileState) -> ProfileState:
        session = state.session
        if session.get("input_chunks"):
            return state

        text_inputs = session.get("text_inputs")
        if not text_inputs:
            raise ValueError("text_inputs are required for collect_input")

        session["input_chunks"] = [
            {"id": idx, "source": "text", "content": content}
            for idx, content in enumerate(text_inputs)
        ]
        return state

    return _runner
