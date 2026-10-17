"""The thread linter proves what is structural and names what needs a reviewer."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from zeo_creator import __version__
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
    assert result["linter"] == {
        "name": "zeocreator.lint-thread",
        "version": __version__,
        "rules": "thread-lint-rules/1",
    }


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


def _with_post(index: int, text: str) -> dict[str, object]:
    draft = _load("pass-basic.json")
    draft["posts"][index] = text  # type: ignore[index]
    return draft


def _codes(draft: dict[str, object]) -> set[str]:
    return {item["code"] for item in lint_thread(draft)["findings"]}  # type: ignore[index]


@pytest.mark.parametrize(
    "bad",
    [
        "\x00",  # NUL
        "\x1b",  # ESC
        "‮",  # right-to-left override
        "⁦",  # bidi isolate
        "​",  # zero-width space
        "‌",  # zero-width non-joiner
        "⁠",  # word joiner
        "﻿",  # byte order mark
        "­",  # soft hyphen
        chr(0x2028),  # line separator
        chr(0x2029),  # paragraph separator
        "\u0085",  # next line
        chr(0xA0),  # no-break space
        "\t",
        "\r",
        "‍",  # a joiner outside an emoji sequence
        "\U000e0041",  # a tag character outside a flag
    ],
)
def test_hidden_and_control_characters_are_found(bad: str) -> None:
    text = f"1/4 A kitchen scale{bad} beats measuring cups for bread."
    assert "T020" in _codes(_with_post(0, text))


@pytest.mark.parametrize(
    "ok",
    [
        "\U0001f468‍\U0001f469‍\U0001f467‍\U0001f466",  # a family, joined
        "\U0001f3f4\U000e0067\U000e0062\U000e0065\U000e006e\U000e0067\U000e007f",  # a flag
        "café \U0001f600",
    ],
)
def test_emoji_sequences_are_not_flagged(ok: str) -> None:
    assert "T020" not in _codes(_with_post(0, f"1/4 A kitchen scale {ok} beats measuring cups."))


def test_a_newline_inside_a_post_is_allowed_but_a_hidden_numbered_post_is_not() -> None:
    assert _codes(_with_post(0, "1/4 First line.\nSecond line, same post.")) == set()
    hidden = _codes(_with_post(0, "1/4 First line.\n\n2/4 A post hiding in the first."))
    assert "T013" in hidden


def test_zero_width_character_cannot_dodge_a_forbidden_phrase() -> None:
    draft = _with_post(0, "1/4 A kitchen scale beats a sur​prise.")
    draft["forbidden_phrases"] = ["surprise"]
    assert "T020" in _codes(draft)


def test_text_glued_to_a_url_is_counted_not_swallowed() -> None:
    glued = "https://x.co/" + "中" * 300
    assert count_post(glued) == 23 + 300
    assert count_post("HTTPS://X.CO/abc") == 23
    assert "T001" in _codes(_with_post(0, "1/4 a b c " + glued))


@pytest.mark.parametrize(
    "number", [chr(0x661) + "/4", chr(0xFF11) + "/" + chr(0xFF14), "01/4", "1/04"]
)
def test_numbering_accepts_only_ascii_digits_without_leading_zeros(number: str) -> None:
    assert "T010" in _codes(_with_post(0, f"{number} A kitchen scale beats cups."))


def test_numbering_needs_an_ascii_space() -> None:
    assert "T010" in _codes(_with_post(0, "1/4" + chr(0xA0) + "A kitchen scale beats cups."))


def test_source_support_is_listed_for_review() -> None:
    assert "source_supports_claims" in NEEDS_REVIEW


def test_duplicate_keys_are_refused(tmp_path: Path) -> None:
    path = tmp_path / "dup.json"
    path.write_text(
        '{"schema":"thread-draft/1","numbering":"n/N","posts":["1/1 a b c"],'
        '"posts":["1/1 x y z"],"source":"s"}',
        encoding="utf-8",
    )
    result = runner.invoke(app, ["lint-thread", "--file", str(path)])
    assert result.exit_code == 2
    assert json.loads(result.stdout)["reason"] == "draft has a duplicate key"


def test_huge_integer_deep_nesting_and_oversize_are_invalid_not_internal(tmp_path: Path) -> None:
    cases = {
        "int.json": '{"schema":' + "9" * 5000 + "}",
        "deep.json": "[" * 100000 + "]" * 100000,
        "big.json": '{"schema":"' + "a" * 1_100_000 + '"}',
    }
    for name, text in cases.items():
        path = tmp_path / name
        path.write_text(text, encoding="utf-8")
        result = runner.invoke(app, ["lint-thread", "--file", str(path)])
        assert result.exit_code == 2, name


def test_stdin_is_decoded_as_utf8() -> None:
    text = (FIXTURES / "pass-basic.json").read_text(encoding="utf-8").replace("kitchen", "küche")
    result = runner.invoke(app, ["lint-thread", "--file", "-"], input=text.encode("utf-8"))
    assert result.exit_code == 0


def test_stated_conventions_are_pinned() -> None:
    result = lint_thread(_load("pass-basic.json"))
    assert result["convention"] == "unicode-nfc-code-points;url=23"
    assert result["limit"] == 280


def test_t002_and_the_n_slash_style() -> None:
    draft = {
        "schema": "thread-draft/1",
        "numbering": "n/",
        "posts": ["1/ https://example.org/a", "2/ A complete statement about bread and flour."],
        "source": "s",
    }
    assert "T002" in _codes(draft)  # type: ignore[arg-type]
    assert (
        _codes({**draft, "posts": ["1/ Bread rises, gently, overnight.", "2/ Weigh it first."]})
        == set()
    )  # type: ignore[arg-type]


def test_link_and_repeat_thresholds() -> None:
    two = _with_post(2, "3/4 Hydration chart: https://example.org/h")
    three = _with_post(2, "3/4 The hydration chart: https://example.org/h")
    assert "T031" in _codes(two)
    assert "T031" not in _codes(three)
    same = _with_post(3, "4/4 " + _load("pass-basic.json")["posts"][1][4:])  # type: ignore[index]
    assert "T040" in _codes(same)


def test_every_declared_bound_is_enforced() -> None:
    base = _load("pass-basic.json")
    with pytest.raises(ThreadDraftError):
        lint_thread({**base, "posts": ["1/1 a"] * 101})
    with pytest.raises(ThreadDraftError):
        lint_thread({**base, "posts": ["1/1 " + "a" * 10_001]})
    with pytest.raises(ThreadDraftError):
        lint_thread({**base, "source": "s" * 10_001})
    with pytest.raises(ThreadDraftError):
        lint_thread({**base, "forbidden_phrases": ["p"] * 201})
    with pytest.raises(ThreadDraftError):
        lint_thread({**base, "forbidden_phrases": ["p" * 201]})


def test_phrases_match_case_and_normalization_insensitively() -> None:
    draft = _with_post(0, "1/4 A kitchen scale beats a SURPRISE at the CAFÉ.")
    draft["forbidden_phrases"] = ["café"]
    assert "T900" in _codes(draft)


def test_findings_are_ordered_by_post_then_code() -> None:
    draft = _with_post(1, "2/4 " + "x" * 300)
    draft["posts"][0] = "1/4 ​" + "y" * 300  # type: ignore[index]
    findings = lint_thread(draft)["findings"]
    keys = [(item["post"] or 0, item["code"]) for item in findings]  # type: ignore[index]
    assert keys == sorted(keys)
