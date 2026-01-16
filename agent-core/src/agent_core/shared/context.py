"""実行コンテキストの構築処理."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import uuid

from .preconditions import (
    PreconditionError,
    validate_evaluate_preconditions,
    validate_job_preconditions,
    validate_profile_preconditions,
)


@dataclass(frozen=True)
class ExecutionContext:
    """エージェント実行時のコンテキスト."""

    mode: str
    text_inputs: list[str]
    file_inputs: list[Any]
    options: dict[str, Any]
    run_id: str

    def as_dict(self) -> dict[str, Any]:
        """コンテキストを辞書に変換する."""
        return {
            "mode": self.mode,
            "text_inputs": list(self.text_inputs),
            "file_inputs": list(self.file_inputs),
            "options": dict(self.options),
            "run_id": self.run_id,
        }


def _normalize_text_inputs(text_inputs: list[str] | None) -> list[str]:
    """空要素を除外し、順序を保持したまま正規化する."""
    if not text_inputs:
        return []
    return [text.strip() for text in text_inputs if text and text.strip()]


def build_execution_context(
    *,
    mode: str,
    text_inputs: list[str] | None,
    file_inputs: list[Any] | None,
    options: dict[str, Any] | None,
    run_id: str | None = None,
) -> ExecutionContext:
    """実行モードに応じたコンテキストを構築する."""
    normalized_texts = _normalize_text_inputs(text_inputs)
    normalized_files = list(file_inputs or [])
    normalized_options = dict(options or {})
    resolved_run_id = run_id or normalized_options.get("run_id")
    if not resolved_run_id:
        resolved_run_id = uuid.uuid4().hex

    if mode == "profile":
        validate_profile_preconditions(
            text_inputs=normalized_texts,
            file_inputs=normalized_files,
        )
    elif mode == "job":
        try:
            validate_job_preconditions(file_inputs=normalized_files)
        except PreconditionError as exc:
            raise ValueError(str(exc)) from exc
    elif mode == "evaluate":
        profile_path = normalized_options.get("profile_path")
        job_path = normalized_options.get("job_path")
        try:
            validate_evaluate_preconditions(
                profile_path=profile_path,
                job_path=job_path,
            )
        except PreconditionError as exc:
            raise ValueError(str(exc)) from exc
    else:
        raise ValueError(f"unsupported mode: {mode}")

    return ExecutionContext(
        mode=mode,
        text_inputs=normalized_texts,
        file_inputs=normalized_files,
        options=normalized_options,
        run_id=resolved_run_id,
    )
