"""保存とバックアップの基盤を検証する。"""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_core.storage import FileStorage, StorageError


def test_storage_rejects_overwrite_when_disabled(tmp_path: Path) -> None:
    """上書き禁止時は保存を中断する。"""
    target = tmp_path / "profile.json"
    target.write_text("old", encoding="utf-8")

    storage = FileStorage()

    with pytest.raises(StorageError):
        storage.save_text(
            path=target,
            content="new",
            allow_overwrite=False,
            create_dirs=True,
            make_backup=True,
        )

    assert target.read_text(encoding="utf-8") == "old"


def test_storage_creates_backup_before_overwrite(tmp_path: Path) -> None:
    """上書き時はバックアップを作成する。"""
    target = tmp_path / "profile.json"
    target.write_text("old", encoding="utf-8")

    storage = FileStorage()

    result = storage.save_text(
        path=target,
        content="new",
        allow_overwrite=True,
        create_dirs=True,
        make_backup=True,
    )

    assert target.read_text(encoding="utf-8") == "new"
    assert result.backup_path is not None
    assert result.backup_path.read_text(encoding="utf-8") == "old"


def test_storage_creates_parent_directory_when_enabled(tmp_path: Path) -> None:
    """保存先が無い場合はディレクトリを作成する。"""
    target = tmp_path / "missing" / "profile.json"

    storage = FileStorage()

    result = storage.save_text(
        path=target,
        content="payload",
        allow_overwrite=False,
        create_dirs=True,
        make_backup=False,
    )

    assert result.path.exists()
    assert result.path.read_text(encoding="utf-8") == "payload"


def test_storage_errors_when_parent_missing_and_creation_disabled(
    tmp_path: Path,
) -> None:
    """保存先が無い場合に作成を許可しないと失敗する。"""
    target = tmp_path / "missing" / "profile.json"
    storage = FileStorage()

    with pytest.raises(StorageError):
        storage.save_text(
            path=target,
            content="payload",
            allow_overwrite=False,
            create_dirs=False,
            make_backup=False,
        )

    assert not target.exists()
