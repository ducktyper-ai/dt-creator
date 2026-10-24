"""The shared newsletter rubric is valid data, applies the 90/80 bar and checks budgets."""

from datetime import UTC, datetime

from zeo_creator.contracts.rubric import (
    CriterionScore,
    ManifestSubject,
    RubricScorecard,
    TextQuote,
)
from zeo_creator.reference.newsletter_rubric import (
    BUDGETS,
    check_length_budgets,
    newsletter_rubric,
    words,
)
from zeo_creator.services.rubric import evaluate_rubric

NOW = datetime(2026, 10, 24, tzinfo=UTC)
SUBJECT = ManifestSubject(brief_id="b1", manifest_id="m1", content_digest="sha256:" + "a" * 64)
TEXT = "The pilot skipped the receipt check. A second paragraph follows."


def rubric():
    return newsletter_rubric(organization_id="org", publication_id="pub", created_at=NOW)


def card(rb, points: dict[str, int]) -> RubricScorecard:
    return RubricScorecard(
        created_at=NOW,
        organization_id="org",
        publication_id="pub",
        scorecard_id="sc1",
        rubric_ref=rb.ref(),
        subject=SUBJECT,
        language="en",
        reviewer_ref="reviewer",
        reviewer_role="agent",
        scores=tuple(
            CriterionScore(
                criterion_id=name,
                state="scored",
                points=value,
                reason="r",
                evidence=() if value >= 4 else (TextQuote(quote="skipped the receipt check"),),
            )
            for name, value in points.items()
        ),
    )


def run(points: dict[str, int]):
    rb = rubric()
    return evaluate_rubric(
        rubric=rb,
        scorecards=[card(rb, points)],
        subject=SUBJECT,
        subject_text=TEXT,
        created_at=NOW,
    )


ALL = ("relevance", "interest", "concision", "voice", "visual-quality")


def test_the_rubric_names_the_five_criteria_and_the_bar() -> None:
    rb = rubric()
    assert [c.criterion_id for c in rb.criteria] == list(ALL)
    assert rb.aggregate_floor is not None
    assert (rb.aggregate_floor.numerator, rb.aggregate_floor.denominator) == (90, 100)


def test_all_fives_pass_and_a_single_four_still_meets_ninety_percent_when_rounded() -> None:
    assert run(dict.fromkeys(ALL, 5)).passed
    assert run({**dict.fromkeys(ALL, 5), "voice": 4}).passed  # 24/25 = 96%


def test_a_dimension_under_eighty_percent_blocks_whatever_the_total() -> None:
    result = run({**dict.fromkeys(ALL, 5), "voice": 3})  # 23/25 = 92% overall, voice 60%
    assert not result.passed


def test_four_fours_and_a_five_miss_the_ninety_bar() -> None:
    assert not run({**dict.fromkeys(ALL, 4), "relevance": 5}).passed  # 21/25 = 84%


def test_budgets_pass_inside_and_name_every_breach_outside() -> None:
    lead = " ".join(["word"] * 380)
    reading = " ".join(["word"] * 65)
    assert (
        check_length_budgets(
            subject="Short subject",
            preheader="Short",
            sections={"lead": lead, "reading": [reading] * 3},
        )
        == ()
    )
    broken = check_length_budgets(
        subject="s" * 56,
        preheader="p" * 91,
        sections={"lead": "too short", "reading": [reading, "x " * 90], "mystery": "x"},
    )
    assert any(item.startswith("subject:") for item in broken)
    assert any(item.startswith("preheader:") for item in broken)
    assert any(item.startswith("lead 1:") for item in broken)
    assert any(item.startswith("reading 2:") for item in broken)
    assert any(item.startswith("mystery:") for item in broken)


def test_words_exclude_urls_and_every_budget_has_an_ordered_range() -> None:
    assert words("see https://example.org/a/b now") == 2
    assert all(low <= high for low, high in BUDGETS.values())
