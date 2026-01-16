"""保存とバックアップの基盤機能."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil


class StorageError(RuntimeError):
    """保存処理に失敗した場合に送出する。"""


@dataclass(frozen=True)
class SaveResult:
    """保存結果をまとめる。"""

    path: Path
    backup_path: Path | None


def _ensure_parent_directory(path: Path, *, create_dirs: bool) -> None:
    """保存先ディレクトリの存在を保証する。"""
    parent = path.parent
    if parent.exists():
        return
    if not create_dirs:
        raise StorageError(
            "save failed because destination directory does not exist; "
            "create the directory or enable create_dirs"
        )
    parent.mkdir(parents=True, exist_ok=True)


def _next_backup_path(path: Path) -> Path:
    """バックアップの保存先パスを決定する。"""
    candidate = path.with_suffix(f"{path.suffix}.bak")
    if not candidate.exists():
        return candidate

    index = 2
    while True:
        candidate = path.with_suffix(f"{path.suffix}.bak{index}")
        if not candidate.exists():
            return candidate
        index += 1


class FileStorage:
    """ファイル保存とバックアップを担保する。"""

    def save_text(
        self,
        *,
        path: Path,
        content: str,
        allow_overwrite: bool,
        create_dirs: bool,
        make_backup: bool,
    ) -> SaveResult:
        """テキスト内容を保存する。"""
        _ensure_parent_directory(path, create_dirs=create_dirs)

        backup_path = None
        if path.exists():
            if not allow_overwrite:
                raise StorageError(
                    "save aborted because destination already exists; "
                    "remove the file or enable overwrite"
                )
            if make_backup:
                backup_path = _next_backup_path(path)
                shutil.copy2(path, backup_path)

        path.write_text(content, encoding="utf-8")
        return SaveResult(path=path, backup_path=backup_path)
