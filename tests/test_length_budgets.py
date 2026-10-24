"""The generic word-budget check names every breach, trims nothing and knows no policy."""

from zeo_creator.services.length_budgets import check_length_budgets, words

BUDGETS = {"lead": (350, 400), "reading": (60, 75)}


def test_inside_budget_is_empty() -> None:
    lead = " ".join(["word"] * 380)
    reading = " ".join(["word"] * 65)
    assert (
        check_length_budgets(
            budgets=BUDGETS,
            sections={"lead": lead, "reading": [reading] * 3},
            subject="Short subject",
            subject_max_chars=55,
            preheader="Short",
            preheader_max_chars=90,
            overall_max_words=1300,
        )
        == ()
    )


def test_every_breach_is_named() -> None:
    reading = " ".join(["word"] * 65)
    broken = check_length_budgets(
        budgets=BUDGETS,
        sections={"lead": "too short", "reading": [reading, "x " * 90], "mystery": "x"},
        subject="s" * 56,
        subject_max_chars=55,
        preheader="p" * 91,
        preheader_max_chars=90,
        overall_max_words=100,
    )
    for prefix in ("subject:", "preheader:", "lead 1:", "reading 2:", "mystery:", "overall:"):
        assert any(item.startswith(prefix) for item in broken), prefix


def test_a_limit_the_caller_leaves_out_is_not_checked() -> None:
    assert check_length_budgets(budgets=BUDGETS, sections={}, subject="s" * 500) == ()


def test_words_exclude_urls() -> None:
    assert words("see https://example.org/a/b now") == 2
