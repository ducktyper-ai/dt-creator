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
        ["help"],
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
    assert str(result["schema"]).startswith("zeocreator.") and str(result["schema"]).endswith("/v1")
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
        ["help"],
        ["help", "--json"],
    ):
        result = runner.invoke(app, args)
        assert result.exit_code == 0, args
        assert _one_result(result.stdout)["ok"] is True, args


def test_runtime_provider_keeps_its_canonical_bytes_until_runtime_reads_json_lines() -> None:
    # The one exception to cli_protocol 1: a Runtime host reads these bytes as published.
    # It ends when a Runtime reader for {"ok": true, "provider": ...} exists, in a versioned release.
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
        result = json.loads(out)
        assert result["outcome"] == "invalid_request", argv
        assert result["schema"] == "zeocreator.error/v1", argv
        assert result["next"] == "zeo-creator help --json", argv
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
    assert json.loads(out) == {
        "ok": False,
        "outcome": "internal",
        "schema": "zeocreator.error/v1",
        "next": cli.INTERNAL_NEXT,
    }
    assert "secret detail" not in out


def test_main_exits_with_the_command_status(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "argv", ["zeo-creator", "doctor"])
    with pytest.raises(SystemExit) as exited:
        cli.main()
    assert exited.value.code == 0
    assert _one_result(capsys.readouterr().out)["ok"] is True


def _leaf_commands(group, prefix=""):
    for name, command in group.commands.items():
        if getattr(command, "commands", None) is not None:
            yield from _leaf_commands(command, f"{prefix}{name} ")
        else:
            yield f"{prefix}{name}"


def test_help_json_catalogues_every_command_exit_code_and_schema(tmp_path: Path) -> None:
    import typer.main

    catalogue = _one_result(runner.invoke(app, ["help", "--json"]).stdout)
    assert catalogue["schema"] == "zeocreator.help/v1"
    listed = {item["command"]: item for item in catalogue["commands"]}
    assert set(listed) == set(_leaf_commands(typer.main.get_command(app)))
    assert [item["code"] for item in catalogue["exit_codes"]] == [0, 1, 2, 20]
    contract = next(o for o in listed["contract-schema"]["options"] if "--name" in o["flags"])
    assert contract["required"] is True
    projection = next(o for o in listed["capabilities"]["options"] if "--projection" in o["flags"])
    assert projection["choices"] == ["manifest", "openai"]
    # Each command's real output carries one of the schema ids the catalogue lists for it.
    for args, command in (
        (["capabilities"], "capabilities"),
        (["capabilities", "--projection", "openai"], "capabilities"),
        (["contracts", "list"], "contracts list"),
        (["contracts", "export", f"--output={tmp_path}"], "contracts export"),
        (["contract-schema", "--name", "content-brief", "--version", "1"], "contract-schema"),
        (["doctor"], "doctor"),
        (["help"], "help"),
    ):
        result = _one_result(runner.invoke(app, args).stdout)
        assert result["schema"] in listed[command]["output_schemas"], args


def test_a_failed_doctor_check_names_its_next_step(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "capability_manifests", lambda: ())
    result = _one_result(runner.invoke(app, ["doctor"]).stdout)
    steps = {item["check"]: item["next"] for item in result["next"]}
    assert "twenty_nine_manifests" in steps
    assert steps["twenty_nine_manifests"].startswith("run: uv tool install --force")
    assert set(steps) == {name for name, ok in result["checks"].items() if not ok}


def test_a_healthy_doctor_has_no_next_steps() -> None:
    assert _one_result(runner.invoke(app, ["doctor"]).stdout)["next"] == []


def test_errors_give_a_reason_and_next_step_without_echoing_input() -> None:
    cases = {
        ("contract-schema", "--name", "no-such-contract", "--version", "1"): (
            "unknown contract",
            "zeo-creator contracts list",
        ),
    }
    for args, (reason, next_step) in cases.items():
        result = runner.invoke(app, list(args))
        body = _one_result(result.stdout)
        assert (body["reason"], body["next"]) == (reason, next_step)
        assert "no-such-contract" not in result.stdout
    assert set(cli.DOCTOR_NEXT) == set(_one_result(runner.invoke(app, ["doctor"]).stdout)["checks"])


HOSTILE = "\x1b[31mHOSTILE-MARKER token=secret-abc\nsecond line"


@pytest.mark.parametrize(
    ("argv", "reason"),
    [
        ([], "missing command"),
        (["no-such-command"], "unknown command"),
        ([f"cmd-{HOSTILE}"], "unknown command"),
        (["capabilities", "--no-such-option"], "unknown option"),
        (["capabilities", f"--bad{HOSTILE}"], "unknown option"),
        (["contract-schema", "--name", "content-brief"], "missing required option"),
        (["capabilities", "--projection", HOSTILE], "invalid option value"),
        (["doctor", HOSTILE], "invalid command line"),
    ],
)
def test_each_usage_error_has_its_exact_reason_and_echoes_nothing(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    argv: list[str],
    reason: str,
) -> None:
    monkeypatch.setattr(sys, "argv", ["zeo-creator", *argv])
    with pytest.raises(SystemExit) as exited:
        cli.main()
    assert exited.value.code == 2
    out = capsys.readouterr().out
    result = json.loads(out)
    assert result["reason"] == reason
    assert result["reason"] in cli.USAGE_REASONS
    assert result["next"] == "zeo-creator help --json"
    for fragment in ("secret-abc", "HOSTILE-MARKER", "second line", "\x1b", "no-such"):
        assert fragment not in out


def test_help_lists_the_closed_set_of_reasons() -> None:
    catalogue = _one_result(runner.invoke(app, ["help", "--json"]).stdout)
    assert catalogue["invalid_request_reasons"] == list(cli.USAGE_REASONS)
