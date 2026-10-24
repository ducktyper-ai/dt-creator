"""`creator.evaluate_rubric@1.0.0`."""

from datetime import datetime

from pydantic import Field
from zeo_core.contracts import CapabilityExample, CapabilityResult, EffectKind
from zeo_core.tools import ToolContext, capability

from zeo_creator.capabilities._rubric_examples import example_request
from zeo_creator.contracts.common import CreatorModel
from zeo_creator.contracts.rubric import (
    ReviewRubric,
    RubricEvaluation,
    RubricRef,
    RubricScorecard,
    Subject,
)
from zeo_creator.errors import CreatorDomainError
from zeo_creator.services.rubric import evaluate_rubric as apply_rubric


class EvaluateRubricRequest(CreatorModel):
    rubric: ReviewRubric
    scorecards: tuple[RubricScorecard, ...] = Field(min_length=1)
    subject: Subject
    subject_text: str
    created_at: datetime
    block_texts: dict[str, str] = Field(default_factory=dict)
    base_rubric: ReviewRubric | None = None
    supported_bases: tuple[RubricRef, ...] | None = None


class EvaluateRubricResponse(CreatorModel):
    evaluation: RubricEvaluation


@capability(
    id="creator.evaluate_rubric@1.0.0",
    description="Apply any review rubric to scorecards: floors, must-pass rules and quoted evidence.",
    effects={EffectKind.READ},
    examples=(CapabilityExample(name="below-floor", request=example_request()),),
    error_codes=("ZEO_CREATOR_RUBRIC_INVALID",),
    tags=("creator", "review", "rubric", "pure"),
    metadata={"execution": "pure-deterministic"},
    projection_name="creator_evaluate_rubric",
)
def evaluate_rubric(
    request: EvaluateRubricRequest,
    ctx: ToolContext,
) -> CapabilityResult[EvaluateRubricResponse]:
    del ctx
    try:
        evaluation = apply_rubric(
            rubric=request.rubric,
            scorecards=request.scorecards,
            subject=request.subject,
            subject_text=request.subject_text,
            created_at=request.created_at,
            block_texts=request.block_texts,
            base_rubric=request.base_rubric,
            supported_bases=request.supported_bases,
        )
    except CreatorDomainError as exc:
        return CapabilityResult.fail(msg=str(exc), code=exc.code)
    return CapabilityResult.ok(
        data=EvaluateRubricResponse(evaluation=evaluation),
        msg=("The rubric passes" if evaluation.passed else "The rubric has blocking findings"),
    )
