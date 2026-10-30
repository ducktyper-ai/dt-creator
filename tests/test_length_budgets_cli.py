"""`zeo-creator check-length-budgets` is the length-budget check for a caller without Python."""

import json

import pytest
from typer.testing import CliRunner

from zeo_creator.cli import app

runner = CliRunner()
WORDS = " ".join(["word"] * 50)
OK = {
    "budgets": {"intro": [40, 80], "item": [5, 60]},
    "sections": {"intro": WORDS, "item": ["a b c d e f"]},
}


def run(document: object, *, args: tuple[str, ...] = ("--file", "-")):
    raw = document if isinstance(document, bytes) else json.dumps(document).encode()
    return runner.invoke(app, ["check-length-budgets", *args], input=raw)


def test_within_budget_is_ok_with_no_breaches() -> None:
    result = run(OK)
    assert result.exit_code == 0
    assert json.loads(result.stdout) == {
        "breaches": [],
        "ok": True,
        "schema": "zeocreator.length-budgets/v1",
    }


def test_every_breach_is_named_and_exits_20() -> None:
    document = {
        **OK,
        "sections": {"intro": "too short", "item": ["a b c d e f"], "mystery": "x y"},
        "subject": "s" * 61,
        "subject_max_chars": 60,
        "overall_max_words": 5,
    }
    result = run(document)
    assert result.exit_code == 20
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    for prefix in ("subject:", "intro 1:", "mystery:", "overall:"):
        assert any(item.startswith(prefix) for item in payload["breaches"]), prefix


def test_reads_a_file(tmp_path) -> None:
    path = tmp_path / "budgets.json"
    path.write_text(json.dumps(OK), encoding="utf-8")
    result = runner.invoke(app, ["check-length-budgets", "--file", str(path)])
    assert result.exit_code == 0


@pytest.mark.parametrize(
    ("document", "reason"),
    [
        (b"{", "input is not valid JSON"),
        (b'{"budgets": {}, "budgets": {}}', "input has a duplicate key"),
        (b"[]", "the document is not a JSON object"),
        (b'{"budgets": {}, "sections": {}, "extra": 1}', None),
        (b'{"budgets": {"a": [3, 1]}, "sections": {}}', "a budget minimum is above its maximum"),
        (
            b'{"budgets": {"a": [1]}, "sections": {}}',
            "each budget must be a [minimum, maximum] pair",
        ),
        (b'{"budgets": {"a": [true, 2]}, "sections": {}}', None),
        (
            b'{"budgets": {}, "sections": {"a": 3}}',
            "each section must be a string or a list of strings",
        ),
        (b'{"budgets": {}, "sections": {}, "overall_max_words": -1}', None),
        (b'{"budgets": {}, "sections": {}, "subject": 3}', "subject and preheader must be strings"),
    ],
)
def test_invalid_input_is_the_error_schema_and_never_echoed(document: bytes, reason) -> None:
    result = run(document)
    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["schema"] == "zeocreator.error/v1"
    assert payload["outcome"] == "invalid_request"
    if reason:
        assert payload["reason"] == reason


def test_input_is_not_echoed_on_stdout() -> None:
    secret = "SECRET-SECTION-NAME"
    result = run({"budgets": {secret: [9, 1]}, "sections": {}})
    assert result.exit_code == 2
    assert secret not in result.stdout


def test_missing_file_is_invalid_request(tmp_path) -> None:
    result = runner.invoke(app, ["check-length-budgets", "--file", str(tmp_path / "nope.json")])
    assert result.exit_code == 2
    assert json.loads(result.stdout)["reason"] == "input file could not be read"


def test_help_catalogue_lists_the_command_with_its_schema() -> None:
    result = runner.invoke(app, ["help", "--json"])
    commands = {item["command"]: item for item in json.loads(result.stdout)["commands"]}
    assert commands["check-length-budgets"]["output_schemas"] == ["zeocreator.length-budgets/v1"]
