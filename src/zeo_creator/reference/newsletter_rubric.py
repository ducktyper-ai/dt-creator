"""The shared newsletter quality bar as data, with its deterministic length-budget check.

Every property uses this one rubric; a masthead may raise a floor, never lower one. The
bar is data the caller owns: 90 of 100 overall and no criterion under 80%. Unsupported
factual claims and a wrong brand identity are the proofreader's hard gate and sit outside
this score. Scorers are supplied by the caller; nothing here calls a model.
"""

import re
from collections.abc import Mapping, Sequence
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

# (minimum words, maximum words) per item. A list-valued section is checked item by item.
BUDGETS: Mapping[str, tuple[int, int]] = {
    "lead": (350, 400),
    "reading": (60, 75),
    "exercise-step": (25, 35),
    "pick": (30, 45),
    "limits-note": (60, 80),
    "cross-promotion": (0, 50),
}
SUBJECT_MAX_CHARS = 55
PREHEADER_MAX_CHARS = 90
OVERALL_MAX_WORDS = 1300

_URL = re.compile(r"https?://\S+")


def newsletter_rubric(
    *, organization_id: str, publication_id: str, created_at: datetime, version: str = "1.0.0"
) -> ReviewRubric:
    return ReviewRubric(
        created_at=created_at,
        organization_id=organization_id,
        publication_id=publication_id,
        rubric_id="house.newsletter",
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


def words(text: str) -> int:
    """Words of the plain alternative, URLs excluded."""
    return len(_URL.sub(" ", text).split())


def check_length_budgets(
    *, subject: str, preheader: str, sections: Mapping[str, str | Sequence[str]]
) -> tuple[str, ...]:
    """Name every budget a draft breaks; empty means within budget. Never trims."""
    broken: list[str] = []
    if len(subject) > SUBJECT_MAX_CHARS:
        broken.append(f"subject: {len(subject)} characters, at most {SUBJECT_MAX_CHARS}")
    if len(preheader) > PREHEADER_MAX_CHARS:
        broken.append(f"preheader: {len(preheader)} characters, at most {PREHEADER_MAX_CHARS}")
    total = 0
    for name, value in sections.items():
        if name not in BUDGETS:
            broken.append(f"{name}: no budget declared")
            continue
        low, high = BUDGETS[name]
        for index, text in enumerate([value] if isinstance(value, str) else value, start=1):
            count = words(text)
            total += count
            if not low <= count <= high:
                broken.append(f"{name} {index}: {count} words, expected {low} to {high}")
    if total > OVERALL_MAX_WORDS:
        broken.append(f"overall: {total} words, at most {OVERALL_MAX_WORDS}")
    return tuple(broken)
