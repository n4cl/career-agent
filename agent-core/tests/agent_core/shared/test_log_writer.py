"""実行ログの保存を検証する。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_core.shared.log_writer import (
    JsonLineLogWriter,
    LogRecord,
    LogWriteError,
)


def _read_first_record(path: Path) -> dict[str, object]:
    """ログファイルの先頭行を辞書として読み取る。"""
    raw = path.read_text(encoding="utf-8").splitlines()[0]
    return json.loads(raw)


def test_log_writer_records_questions_warnings_and_input_refs(tmp_path: Path) -> None:
    """質問・警告・入力参照が記録される。"""
    log_path = tmp_path / "logs" / "run.log"
    writer = JsonLineLogWriter(log_path=log_path, create_dirs=True)

    record = LogRecord(
        questions=["質問1"],
        warnings=["警告1"],
        input_refs=["profile.txt"],
        metadata={"run_id": "r1"},
    )

    writer.write(record)

    payload = _read_first_record(log_path)
    assert payload["questions"] == ["質問1"]
    assert payload["warnings"] == ["警告1"]
    assert payload["input_refs"] == ["profile.txt"]
    assert payload["metadata"] == {"run_id": "r1"}


def test_log_writer_masks_input_refs_when_policy_enabled(tmp_path: Path) -> None:
    """機微情報はマスクポリシーに従って変換される。"""
    log_path = tmp_path / "run.log"
    writer = JsonLineLogWriter(
        log_path=log_path,
        create_dirs=True,
        mask_mode="hash",
        mask_fields={"input_refs"},
    )

    record = LogRecord(
        questions=["質問1"],
        warnings=["警告1"],
        input_refs=["secret.txt"],
        metadata={},
    )

    writer.write(record)

    payload = _read_first_record(log_path)
    masked_value = payload["input_refs"][0]
    assert masked_value != "secret.txt"
    assert isinstance(masked_value, str)
    assert len(masked_value) == 64


def test_log_writer_fails_when_directory_missing_and_creation_disabled(
    tmp_path: Path,
) -> None:
    """保存先が無い場合に作成を許可しないと失敗する。"""
    log_path = tmp_path / "missing" / "run.log"
    writer = JsonLineLogWriter(log_path=log_path, create_dirs=False)

    record = LogRecord(
        questions=[],
        warnings=["warn"],
        input_refs=[],
        metadata={},
    )

    with pytest.raises(LogWriteError):
        writer.write(record)
