from __future__ import annotations

from typer.testing import CliRunner

from profile_agent.cli.app import app
from profile_agent import __version__


runner = CliRunner()


def test_profile_group_lists_subcommands() -> None:
    """`profile --help` が create/update/show を案内することを検証する。"""
    result = runner.invoke(app, ["profile", "--help"])

    assert result.exit_code == 0
    for command in ("create", "update", "show"):
        assert command in result.stdout


def test_create_command_exposes_expected_options() -> None:
    """create コマンドに必要オプションが表示されるか確認する。"""
    result = runner.invoke(app, ["profile", "create", "--help"])

    assert result.exit_code == 0
    assert "--file" in result.stdout
    assert "--force" in result.stdout
    assert "--no-interactive" in result.stdout


def test_update_command_exposes_expected_options() -> None:
    """update コマンドの引数群を案内できているかを検証する。"""
    result = runner.invoke(app, ["profile", "update", "--help"])

    assert result.exit_code == 0
    assert "--fields" in result.stdout
    assert "--file" in result.stdout
    assert "--no-interactive" in result.stdout


def test_show_command_exposes_expected_options() -> None:
    """show コマンドが text/json/raw オプションを提供しているか確認する。"""
    result = runner.invoke(app, ["profile", "show", "--help"])

    assert result.exit_code == 0
    assert "--format" in result.stdout
    assert "text|json" in result.stdout
    assert "--raw" in result.stdout


def test_version_option_outputs_package_version() -> None:
    """`--version` オプションがパッケージのバージョンを表示するか検証する。"""
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert "career-agent" in result.stdout
    assert __version__ in result.stdout
