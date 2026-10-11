"""Other seats operate the CLI through documented verbs, JSON and fixed exit codes."""

import json
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

import zeo_creator.cli as cli
from zeo_creator.cli import app

runner = CliRunner()


def test_every_command_has_help() -> None:
    for args in (
        [],
        ["capabilities"],
        ["contracts", "list"],
        ["contracts", "export"],
        ["contract-schema"],
        ["doctor"],
        ["runtime-provider"],
    ):
        result = runner.invoke(app, [*args, "--help"])
        assert result.exit_code == 0, args


def _one_result(stdout: str) -> dict[str, object]:
    lines = stdout.splitlines()
    assert len(lines) == 1, lines[:3]
    result = json.loads(lines[0])
    assert isinstance(result, dict)
    assert "ok" in result
    assert "event" not in result
    return result


def test_every_command_prints_one_json_result_line(tmp_path: Path) -> None:
    for args in (
        ["--version"],
        ["capabilities"],
        ["capabilities", "--json"],
        ["capabilities", "--projection", "openai"],
        ["contracts", "list"],
        ["contracts", "list", "--json"],
        ["contracts", "export", f"--output={tmp_path}"],
        ["contract-schema", "--name", "content-brief", "--version", "1"],
        ["doctor"],
        ["doctor", "--json"],
    ):
        result = runner.invoke(app, args)
        assert result.exit_code == 0, args
        assert _one_result(result.stdout)["ok"] is True, args


def test_runtime_provider_keeps_its_canonical_bytes_until_runtime_reads_json_lines() -> None:
    # The one exception to cli_protocol 1 (ZEOCREATOR-SOW-19): Runtime reads these bytes.
    # It ends when zeo-rt confirms a reader for {"ok": true, "provider": ...}.
    from zeo_core.adapters.runtime_host.canonical import canonical_bytes

    from zeo_creator.provider import provider_inventory

    result = runner.invoke(app, ["runtime-provider"])
    assert result.exit_code == 0
    assert result.stdout == canonical_bytes(provider_inventory()).decode() + "\n"
    assert "ok" not in json.loads(result.stdout)


def test_bad_input_exits_two() -> None:
    assert runner.invoke(app, ["no-such-command"]).exit_code == 2
    assert runner.invoke(app, ["capabilities", "--no-such-option"]).exit_code == 2
    unknown = runner.invoke(
        app, ["contract-schema", "--name", "no-such-contract", "--version", "1"]
    )
    assert unknown.exit_code == 2
    assert _one_result(unknown.stdout)["outcome"] == "invalid_request"
    assert "no-such-contract" not in unknown.stdout


def test_a_usage_error_answers_invalid_on_stdout(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    for argv in ([], ["no-such-command"], ["capabilities", "--no-such-option"]):
        monkeypatch.setattr(sys, "argv", ["zeo-creator", *argv])
        with pytest.raises(SystemExit) as exited:
            cli.main()
        assert exited.value.code == 2, argv
        out = capsys.readouterr().out
        assert json.loads(out) == {"ok": False, "outcome": "invalid_request"}, argv
        assert "no-such" not in out


def test_a_failed_check_is_refused_with_twenty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "capability_manifests", lambda: ())
    result = runner.invoke(app, ["doctor", "--json"])
    assert result.exit_code == 20
    assert json.loads(result.stdout)["ok"] is False


def test_an_internal_error_exits_one_without_detail(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def broken() -> None:
        raise RuntimeError("secret detail")

    monkeypatch.setattr(cli, "capability_manifests", broken)
    monkeypatch.setattr(sys, "argv", ["zeo-creator", "capabilities", "--json"])
    with pytest.raises(SystemExit) as exited:
        cli.main()
    assert exited.value.code == 1
    out = capsys.readouterr().out
    assert json.loads(out) == {"ok": False, "outcome": "internal"}
    assert "secret detail" not in out


def test_main_exits_with_the_command_status(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "argv", ["zeo-creator", "doctor"])
    with pytest.raises(SystemExit) as exited:
        cli.main()
    assert exited.value.code == 0
    assert _one_result(capsys.readouterr().out)["ok"] is True
