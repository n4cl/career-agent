"""実行ログを所定の保存先に記録する。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal
import hashlib
import json

MaskMode = Literal["none", "redact", "hash"]


class LogWriteError(RuntimeError):
    """ログ保存に失敗した場合に送出する。"""


@dataclass(frozen=True)
class LogRecord:
    """ログに保存する実行情報."""

    questions: list[str]
    warnings: list[str]
    input_refs: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)


def _ensure_parent_directory(path: Path, *, create_dirs: bool) -> None:
    """ログ保存先ディレクトリの存在を保証する。"""
    parent = path.parent
    if parent.exists():
        return
    if not create_dirs:
        raise LogWriteError(
            "log destination does not exist; "
            "create the directory or enable create_dirs"
        )
    parent.mkdir(parents=True, exist_ok=True)


def _apply_mask(value: str, *, mode: MaskMode) -> str:
    """マスク方針に従って値を変換する。"""
    if mode == "none":
        return value
    if mode == "redact":
        return "[REDACTED]"
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return digest


def _mask_list(values: list[str], *, mode: MaskMode) -> list[str]:
    """リスト内の値をマスク方針で変換する。"""
    return [_apply_mask(value, mode=mode) for value in values]


def _build_payload(
    record: LogRecord,
    *,
    mask_mode: MaskMode,
    mask_fields: set[str],
) -> dict[str, Any]:
    """ログの保存ペイロードを構築する。"""
    questions = record.questions
    warnings = record.warnings
    input_refs = record.input_refs

    if "questions" in mask_fields:
        questions = _mask_list(questions, mode=mask_mode)
    if "warnings" in mask_fields:
        warnings = _mask_list(warnings, mode=mask_mode)
    if "input_refs" in mask_fields:
        input_refs = _mask_list(input_refs, mode=mask_mode)

    return {
        "questions": questions,
        "warnings": warnings,
        "input_refs": input_refs,
        "metadata": dict(record.metadata),
    }


class JsonLineLogWriter:
    """JSON Lines で実行ログを追記する。"""

    def __init__(
        self,
        *,
        log_path: Path,
        create_dirs: bool = True,
        mask_mode: MaskMode = "none",
        mask_fields: set[str] | None = None,
    ) -> None:
        self._log_path = log_path
        self._create_dirs = create_dirs
        self._mask_mode = mask_mode
        self._mask_fields = set(mask_fields or [])

    def write(self, record: LogRecord) -> None:
        """ログを追記保存する。"""
        _ensure_parent_directory(self._log_path, create_dirs=self._create_dirs)
        payload = _build_payload(
            record,
            mask_mode=self._mask_mode,
            mask_fields=self._mask_fields,
        )
        serialized = json.dumps(payload, ensure_ascii=False)
        with self._log_path.open("a", encoding="utf-8") as handle:
            handle.write(serialized + "\n")
