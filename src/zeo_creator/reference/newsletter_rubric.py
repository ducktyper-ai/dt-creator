"""An illustrative newsletter rubric, as data. It is NOT the production policy.

Newsroom owns the production newsletter criteria, weights, pass threshold, section budgets
and per-property configuration, and changes them without a Creator release. This example
shows the shape: five scored criteria, an 80 of 100 bar with no criterion under 60%, and the
budgets a caller would pass to `zeo_creator.services.length_budgets.check_length_budgets`.
Scorers are supplied by the caller; nothing here calls a model. Do not cite
`example.newsletter` as a house policy.
"""

from collections.abc import Mapping
from datetime import datetime

from zeo_creator.contracts.rubric import (
    AggregateFloor,
    Criterion,
    CriterionKind,
    ReviewRubric,
    Rounding,
    RubricScope,
)

CRITERIA = (
    ("relevance", "Each item matches what the intended reader is looking for."),
    ("clarity", "Each section says one thing plainly."),
    ("brevity", "Every section stays inside its length budget."),
    ("tone", "The tone is consistent from start to finish."),
    ("layout", "Headings and spacing are consistent and the text-only reading works."),
)

# Example budgets: (minimum words, maximum words) per item.
EXAMPLE_BUDGETS: Mapping[str, tuple[int, int]] = {
    "intro": (40, 80),
    "item": (20, 60),
    "outro": (10, 40),
}
EXAMPLE_SUBJECT_MAX_CHARS = 60
EXAMPLE_PREHEADER_MAX_CHARS = 100
EXAMPLE_OVERALL_MAX_WORDS = 400


def newsletter_rubric(
    *, organization_id: str, publication_id: str, created_at: datetime, version: str = "1.0.0"
) -> ReviewRubric:
    return ReviewRubric(
        created_at=created_at,
        organization_id=organization_id,
        publication_id=publication_id,
        rubric_id="example.newsletter",
        rubric_version=version,
        medium="newsletter",
        scope=RubricScope.HOUSE,
        languages=("en",),
        criteria=tuple(
            Criterion(
                criterion_id=name,
                kind=CriterionKind.SCORED,
                rule_ref=f"newsletter.{name}",
                guidance=guidance,
                max_points=5,
                floor=3,
                weight=1,
            )
            for name, guidance in CRITERIA
        ),
        aggregate_floor=AggregateFloor(
            numerator=80, denominator=100, rounding=Rounding.HALF_UP_PERCENT
        ),
    )
