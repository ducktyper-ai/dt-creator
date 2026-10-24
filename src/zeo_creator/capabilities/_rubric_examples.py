"""Neutral synthetic example for creator.evaluate_rubric: no real publication or policy."""

from datetime import UTC, datetime
from typing import Any

from zeo_creator.contracts.rubric import (
    Criterion,
    CriterionKind,
    CriterionScore,
    ManifestSubject,
    ReviewRubric,
    RubricScope,
    RubricScorecard,
    TextQuote,
)

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
SUBJECT = ManifestSubject(
    brief_id="brief-1", manifest_id="manifest-1", content_digest="sha256:" + "a" * 64
)
TEXT = "A short synthetic piece used only to show the shape of an evaluation."


def example_rubric() -> ReviewRubric:
    return ReviewRubric(
        created_at=NOW,
        organization_id="example-org",
        publication_id="example-publication",
        rubric_id="example.piece",
        rubric_version="1.0.0",
        medium="example-piece",
        scope=RubricScope.HOUSE,
        languages=("en",),
        criteria=(
            Criterion(
                criterion_id="clarity",
                kind=CriterionKind.SCORED,
                rule_ref="example.clarity",
                guidance="The piece is easy to follow.",
                max_points=5,
                floor=3,
                weight=2,
            ),
            Criterion(
                criterion_id="supported",
                kind=CriterionKind.MUST_PASS,
                rule_ref="example.supported",
                guidance="Every claim is supported.",
            ),
        ),
    )


def example_scorecard(rubric: ReviewRubric) -> RubricScorecard:
    return RubricScorecard(
        created_at=NOW,
        organization_id=rubric.organization_id,
        publication_id=rubric.publication_id,
        scorecard_id="scorecard-1",
        rubric_ref=rubric.ref(),
        subject=SUBJECT,
        language="en",
        reviewer_ref="example-reviewer",
        reviewer_role="agent",
        scores=(
            CriterionScore(
                criterion_id="clarity",
                state="scored",
                points=2,
                reason="Dense.",
                evidence=(TextQuote(quote="short synthetic piece"),),
            ),
            CriterionScore(criterion_id="supported", state="scored", passed=True, reason="Fine."),
        ),
    )


def example_request() -> dict[str, Any]:
    rubric = example_rubric()
    return {
        "rubric": rubric.model_dump(mode="json"),
        "scorecards": [example_scorecard(rubric).model_dump(mode="json")],
        "subject": SUBJECT.model_dump(mode="json"),
        "subject_text": TEXT,
        "created_at": NOW.isoformat(),
    }
