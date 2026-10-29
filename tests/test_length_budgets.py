"""The generic word-budget check names every breach, trims nothing and knows no policy."""

from zeo_creator.services.length_budgets import check_length_budgets, words

BUDGETS = {"intro": (40, 80), "item": (20, 60)}


def test_inside_budget_is_empty() -> None:
    intro = " ".join(["word"] * 50)
    item = " ".join(["word"] * 30)
    assert (
        check_length_budgets(
            budgets=BUDGETS,
            sections={"intro": intro, "item": [item] * 3},
            subject="Short subject",
            subject_max_chars=60,
            preheader="Short",
            preheader_max_chars=100,
            overall_max_words=400,
        )
        == ()
    )


def test_every_breach_is_named() -> None:
    item = " ".join(["word"] * 30)
    broken = check_length_budgets(
        budgets=BUDGETS,
        sections={"intro": "too short", "item": [item, "x " * 90], "mystery": "x"},
        subject="s" * 61,
        subject_max_chars=60,
        preheader="p" * 101,
        preheader_max_chars=100,
        overall_max_words=100,
    )
    for prefix in ("subject:", "preheader:", "intro 1:", "item 2:", "mystery:", "overall:"):
        assert any(item.startswith(prefix) for item in broken), prefix


def test_an_undeclared_section_still_counts_toward_the_overall_limit() -> None:
    broken = check_length_budgets(
        budgets=BUDGETS,
        sections={"intro": " ".join(["word"] * 50), "mystery": " ".join(["x"] * 60)},
        overall_max_words=100,
    )
    assert any(item.startswith("mystery:") for item in broken)
    assert any(item.startswith("overall:") for item in broken)


def test_a_limit_the_caller_leaves_out_is_not_checked() -> None:
    assert check_length_budgets(budgets=BUDGETS, sections={}, subject="s" * 500) == ()


def test_words_exclude_urls() -> None:
    assert words("see https://example.org/a/b now") == 2
