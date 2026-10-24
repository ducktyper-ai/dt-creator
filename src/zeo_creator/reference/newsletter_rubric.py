"""An illustrative newsletter rubric, as data. It is NOT the production policy.

Newsroom owns the production newsletter criteria, weights, pass threshold, section budgets
and per-property configuration, and changes them without a Creator release. This example
shows the shape: five scored criteria, a 90 of 100 bar with no criterion under 80%, and the
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
    ("relevance", "Every item answers a question this property's reader actually has."),
    (
        "interest",
        "The lead earns the open and each reading adds something the reader did not have.",
    ),
    ("concision", "Every section stays inside its length budget and nothing is padding."),
    (
        "voice",
        "The property's own voice and source policy hold; no sponsor or product endorsement.",
    ),
    ("visual-quality", "Hierarchy, spacing and the text-only reading are clean."),
)

# Example budgets: (minimum words, maximum words) per item.
EXAMPLE_BUDGETS: Mapping[str, tuple[int, int]] = {
    "lead": (350, 400),
    "reading": (60, 75),
    "exercise-step": (25, 35),
    "pick": (30, 45),
    "limits-note": (60, 80),
    "cross-promotion": (0, 50),
}
EXAMPLE_SUBJECT_MAX_CHARS = 55
EXAMPLE_PREHEADER_MAX_CHARS = 90
EXAMPLE_OVERALL_MAX_WORDS = 1300


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
                floor=4,
                weight=1,
            )
            for name, guidance in CRITERIA
        ),
        aggregate_floor=AggregateFloor(
            numerator=90, denominator=100, rounding=Rounding.HALF_UP_PERCENT
        ),
    )
