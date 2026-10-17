"""The thread linter proves what is structural and names what needs a reviewer."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from zeo_creator.cli import app
from zeo_creator.thread_lint import (
    NEEDS_REVIEW,
    POST_LIMIT,
    ThreadDraftError,
    count_post,
    lint_thread,
)

FIXTURES = Path(__file__).parent / "fixtures" / "threads"
runner = CliRunner()

# Each failing fixture trips exactly the rule it is named for.
EXPECTED = {
    "fail-too-long.json": {"T001"},
    "fail-numbering-order.json": {"T011"},
    "fail-numbering-total.json": {"T012"},
    "fail-numbering-missing.json": {"T010"},
    "fail-link-dependent.json": {"T031"},
    "fail-no-source.json": {"T050"},
    "fail-last-repeats.json": {"T040"},
    "fail-forbidden-phrase.json": {"T900"},
}


def _load(name: str) -> dict[str, object]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_passing_fixture_is_clean_and_still_lists_what_needs_review() -> None:
    result = lint_thread(_load("pass-basic.json"))
    assert result["ok"] is True
    assert result["findings"] == []
    assert result["needs_review"] == list(NEEDS_REVIEW)


@pytest.mark.parametrize(("name", "codes"), sorted(EXPECTED.items()))
def test_each_failing_fixture_trips_its_rule(name: str, codes: set[str]) -> None:
    result = lint_thread(_load(name))
    assert result["ok"] is False
    assert {item["code"] for item in result["findings"]} == codes  # type: ignore[index]


def test_length_counts_numbering_and_weighs_urls_as_23() -> None:
    assert count_post("1/2 " + "a" * (POST_LIMIT - 4)) == POST_LIMIT
    assert count_post("see https://example.org/a-very-long-path-that-keeps-going ok") == 4 + 23 + 3


def test_limit_boundary() -> None:
    draft = _load("pass-basic.json")
    draft["posts"][0] = "1/4 " + "a" * (POST_LIMIT - 4)  # type: ignore[index]
    assert lint_thread(draft)["ok"] is True
    draft["posts"][0] = "1/4 " + "a" * (POST_LIMIT - 3)  # type: ignore[index]
    assert lint_thread(draft)["ok"] is False


def test_length_counts_code_points_after_nfc() -> None:
    assert count_post("é") == 1  # e + combining accent composes to one code point
    assert count_post("\U0001f600") == 1  # an emoji is one code point, not bytes


@pytest.mark.parametrize(
    "bad",
    [
        [],
        {"schema": "thread-draft/1", "numbering": "n/N", "posts": []},
        {"schema": "thread-draft/1", "numbering": "x", "posts": ["1/1 a"]},
        {"schema": "thread-draft/1", "numbering": "n/N", "posts": [1]},
        {"schema": "thread-draft/1", "numbering": "n/N", "posts": ["1/1 a"], "extra": 1},
        {
            "schema": "thread-draft/1",
            "numbering": "n/N",
            "posts": ["1/1 a"],
            "forbidden_phrases": [""],
        },
    ],
)
def test_malformed_draft_is_refused(bad: object) -> None:
    with pytest.raises(ThreadDraftError):
        lint_thread(bad)


def test_cli_exit_codes_and_one_json_line() -> None:
    clean = runner.invoke(app, ["lint-thread", "--file", str(FIXTURES / "pass-basic.json")])
    assert clean.exit_code == 0
    assert json.loads(clean.stdout)["schema"] == "zeocreator.thread-lint/v1"
    failing = runner.invoke(app, ["lint-thread", "--file", str(FIXTURES / "fail-too-long.json")])
    assert failing.exit_code == 20
    assert len(failing.stdout.splitlines()) == 1
    invalid = runner.invoke(app, ["lint-thread", "--file", str(FIXTURES / "invalid-schema.json")])
    assert invalid.exit_code == 2
    assert json.loads(invalid.stdout)["outcome"] == "invalid_request"


def test_cli_invalid_input_never_echoes_it(tmp_path: Path) -> None:
    secret = "do-not-echo-this-marker"
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"schema": secret}), encoding="utf-8")
    result = runner.invoke(app, ["lint-thread", "--file", str(path)])
    assert result.exit_code == 2
    assert secret not in result.stdout
    missing = runner.invoke(app, ["lint-thread", "--file", str(tmp_path / secret)])
    assert missing.exit_code == 2
    assert secret not in missing.stdout
    notjson = tmp_path / "x.json"
    notjson.write_text("{" + secret, encoding="utf-8")
    assert secret not in runner.invoke(app, ["lint-thread", "--file", str(notjson)]).stdout


def test_cli_reads_standard_input() -> None:
    text = (FIXTURES / "pass-basic.json").read_text(encoding="utf-8")
    result = runner.invoke(app, ["lint-thread", "--file", "-"], input=text)
    assert result.exit_code == 0


def test_help_catalogue_lists_the_command_with_its_schema() -> None:
    result = runner.invoke(app, ["help", "--json"])
    commands = {item["command"]: item for item in json.loads(result.stdout)["commands"]}
    assert commands["lint-thread"]["output_schemas"] == ["zeocreator.thread-lint/v1"]


def test_skill_example_is_the_passing_fixture_and_lints_clean() -> None:
    skill = (Path(__file__).parent.parent / "skills" / "thread-authoring" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    draft = _load("pass-basic.json")
    for post in draft["posts"]:  # type: ignore[attr-defined]
        assert post in skill
    assert skill.startswith("---\nname: thread-authoring\n")
