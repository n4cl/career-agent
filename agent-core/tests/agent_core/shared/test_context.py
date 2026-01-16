"""実行コンテキストの構築と正規化を検証する。"""

from __future__ import annotations

import pytest

from agent_core.shared.context import ExecutionContext, build_execution_context


def test_build_execution_context_normalizes_text_inputs() -> None:
    """空要素を除外し、入力順を維持する。"""
    context = build_execution_context(
        mode="profile",
        text_inputs=["  first ", "", "second"],
        file_inputs=None,
        options={"interactive": True},
    )
    assert context.text_inputs == ["first", "second"]


def test_build_execution_context_allows_empty_profile_inputs() -> None:
    """プロフィールは空入力で開始できる。"""
    context = build_execution_context(
        mode="profile",
        text_inputs=None,
        file_inputs=None,
        options={"interactive": True},
    )
    assert context.text_inputs == []


def test_build_execution_context_requires_job_inputs() -> None:
    """求人は入力が無い場合に例外を返す。"""
    with pytest.raises(ValueError):
        build_execution_context(
            mode="job",
            text_inputs=None,
            file_inputs=None,
            options=None,
        )


def test_build_execution_context_requires_evaluate_inputs() -> None:
    """評価は必須入力が欠ける場合に例外を返す。"""
    with pytest.raises(ValueError):
        build_execution_context(
            mode="evaluate",
            text_inputs=None,
            file_inputs=None,
            options=None,
        )


def test_execution_context_defaults_options() -> None:
    """未指定オプションは既定値で補完する。"""
    context = build_execution_context(
        mode="profile",
        text_inputs=["hello"],
        file_inputs=None,
        options=None,
    )
    assert context.options == {}


def test_execution_context_preserves_file_inputs_order(tmp_path) -> None:
    """ファイル入力の順序を保持する。"""
    first = tmp_path / "a.txt"
    second = tmp_path / "b.txt"
    first.write_text("a")
    second.write_text("b")
    context = build_execution_context(
        mode="job",
        text_inputs=None,
        file_inputs=[first, second],
        options=None,
    )
    assert context.file_inputs == [first, second]


def test_execution_context_exports_view() -> None:
    """辞書変換時に必要項目を含める。"""
    context = ExecutionContext(
        mode="profile",
        text_inputs=["hello"],
        file_inputs=[],
        options={"interactive": True},
    )
    payload = context.as_dict()
    assert payload["mode"] == "profile"
    assert payload["text_inputs"] == ["hello"]
    assert payload["file_inputs"] == []
    assert payload["options"] == {"interactive": True}
