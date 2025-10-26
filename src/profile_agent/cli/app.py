"""CLI エントリーポイント定義."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal, Optional

import typer

from profile_agent import __version__


app = typer.Typer(help="キャリアエージェントの CLI ツール。")
profile_app = typer.Typer(help="プロフィール管理コマンド")
app.add_typer(profile_app, name="profile")


def _not_implemented(command_name: str) -> None:
    """実装前のコマンドに対して一貫したメッセージを表示する."""
    typer.echo(f"{command_name} は現在実装中です。", err=True)
    raise typer.Exit(code=1)


def _version_callback(value: Optional[bool]) -> Optional[bool]:
    """`--version` オプションを処理し、バージョン表示のみ行う."""
    if value:
        typer.echo(f"career-agent version {__version__}")
        raise typer.Exit()
    return value


@app.callback()
def main(
    version: Annotated[
        Optional[bool],
        typer.Option(
            "--version",
            is_eager=True,
            callback=_version_callback,
            help="バージョン情報を表示して終了する。",
        ),
    ] = None,
) -> None:
    """CLI ルートエントリ."""


@profile_app.command("create")
def create_profile(
    files: Annotated[
        Optional[list[Path]],
        typer.Option(
            "--file",
            "-f",
            exists=True,
            readable=True,
            dir_okay=False,
            help="プロフィール生成に利用するテキストファイル（複数指定可）。",
        ),
    ] = None,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            help="既存プロフィールがあっても上書きする。",
        ),
    ] = False,
    no_interactive: Annotated[
        bool,
        typer.Option(
            "--no-interactive",
            help="ヒアリング質問をスキップして非対話モードで実行する。",
        ),
    ] = False,
) -> None:
    """プロフィールの新規作成コマンド."""
    _not_implemented("profile create")


@profile_app.command("update")
def update_profile(
    fields: Annotated[
        Optional[list[str]],
        typer.Option(
            "--fields",
            help="更新対象のプロフィールフィールドを複数指定する。",
        ),
    ] = None,
    files: Annotated[
        Optional[list[Path]],
        typer.Option(
            "--file",
            "-f",
            exists=True,
            readable=True,
            dir_okay=False,
            help="更新に利用する追加テキストファイル（複数指定可）。",
        ),
    ] = None,
    no_interactive: Annotated[
        bool,
        typer.Option(
            "--no-interactive",
            help="ヒアリング質問をスキップして非対話モードで実行する。",
        ),
    ] = False,
) -> None:
    """プロフィールの部分更新コマンド."""
    _not_implemented("profile update")


@profile_app.command("show")
def show_profile(
    format_: Annotated[
        Literal["text", "json"],
        typer.Option(
            "--format",
            "-F",
            case_sensitive=False,
            help="表示形式。text か json を選択。",
        ),
    ] = "text",
    raw: Annotated[
        bool,
        typer.Option(
            "--raw",
            help="整形せずに保存済み JSON をそのまま出力する。",
        ),
    ] = False,
) -> None:
    """保存済みプロフィールの表示コマンド."""
    _not_implemented("profile show" + (" (raw)" if raw else ""))
