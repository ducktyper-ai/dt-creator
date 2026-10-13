"""Pure, deterministic application of a review rubric to scorecards.

No criterion, threshold, lexicon or house policy lives here. The engine applies whatever
rubric it is given, refuses a masthead rubric that lowers its house base, and fails closed:
a missing score, an unknown score or a missing input is never a pass.
"""

from collections.abc import Mapping, Sequence
from datetime import datetime

from zeo_creator.contracts.common import canonical_digest, digest_is_current, stable_id
from zeo_creator.contracts.rubric import (
    AggregateFloor,
    Criterion,
    CriterionKind,
    CriterionScore,
    FindingKind,
    ReviewRubric,
    Rounding,
    RubricEvaluation,
    RubricFinding,
    RubricRef,
    RubricScorecard,
    Subject,
    TextQuote,
)
from zeo_creator.errors import CreatorDomainError

INVALID = "ZEO_CREATOR_RUBRIC_INVALID"

_FINDING_CODES = {
    FindingKind.BELOW_FLOOR: "ZEO_CREATOR_RUBRIC_BELOW_FLOOR",
    FindingKind.MUST_PASS_FAILED: "ZEO_CREATOR_RUBRIC_MUST_PASS_FAILED",
    FindingKind.UNKNOWN_SCORE: "ZEO_CREATOR_RUBRIC_UNKNOWN_SCORE",
    FindingKind.MISSING_SCORE: "ZEO_CREATOR_RUBRIC_MISSING_SCORE",
    FindingKind.AGGREGATE_BELOW_FLOOR: "ZEO_CREATOR_RUBRIC_AGGREGATE_BELOW_FLOOR",
}


def _refuse(reason: str) -> CreatorDomainError:
    return CreatorDomainError(INVALID, reason)


def _meets(floor: AggregateFloor, points: int, maximum: int) -> bool:
    if maximum == 0:
        return True
    if floor.rounding == Rounding.HALF_UP_PERCENT:
        percent = (2 * points * 100 + maximum) // (2 * maximum)
        return percent >= floor.numerator
    return points * floor.denominator >= floor.numerator * maximum


def check_masthead_raises_only(
    rubric: ReviewRubric,
    base: ReviewRubric | None,
    supported: Sequence[RubricRef] | None,
) -> None:
    """Refuse a rubric that lowers, drops or reshapes anything its house base fixes."""
    ref = rubric.base_rubric_ref
    if ref is None:
        return
    if base is None or not digest_is_current(base) or base.ref() != ref:
        raise _refuse("the base rubric is missing or does not match its pinned digest")
    if supported is None or ref not in supported:
        raise _refuse("the pinned base is not a version the house lists as supported")
    if rubric.medium != base.medium:
        raise _refuse("a rubric builds on a base of the same medium")
    own = {item.criterion_id: item for item in rubric.criteria}
    for original in base.criteria:
        item = own.get(original.criterion_id)
        if item is None:
            raise _refuse("a base criterion is missing")
        if item.kind != original.kind:
            raise _refuse("a base criterion changed kind")
        if item.kind == CriterionKind.SCORED:
            assert item.max_points is not None and item.floor is not None
            if item.max_points != original.max_points:
                raise _refuse("a criterion's max_points differs from the base")
            assert original.floor is not None
            if item.floor < original.floor:
                raise _refuse("a criterion's floor is lower than the base's")
            if item.weight != original.weight and (
                item.criterion_id not in rubric.declared_weight_changes
            ):
                raise _refuse("a changed weight is not declared")
    if base.aggregate_floor is not None:
        floor = rubric.aggregate_floor
        if floor is None or floor.rounding != base.aggregate_floor.rounding:
            raise _refuse("the aggregate floor is missing or uses a different rounding")
        if floor.numerator * base.aggregate_floor.denominator < (
            base.aggregate_floor.numerator * floor.denominator
        ):
            raise _refuse("the aggregate floor is lower than the base's")


def _check_text(score: CriterionScore, text: str, blocks: Mapping[str, str]) -> None:
    for item in score.evidence:
        if not isinstance(item, TextQuote):
            continue
        haystack = text if item.block_id is None else blocks.get(item.block_id)
        if haystack is None or item.quote not in haystack:
            raise _refuse("a quoted passage does not occur in the subject's text")


def _effective(
    scorecards: Sequence[RubricScorecard], primary: RubricScorecard, criterion: Criterion
) -> tuple[CriterionScore | None, bool]:
    """The score that stands for a criterion, and whether a human re-scored it."""
    base = next((s for s in primary.scores if s.criterion_id == criterion.criterion_id), None)
    rescored = [
        s
        for card in scorecards
        if card is not primary
        for s in card.scores
        if s.criterion_id == criterion.criterion_id
    ]
    if not rescored:
        return base, False
    if criterion.backing_check_id is not None:
        raise _refuse("a criterion backed by a producer check cannot be re-scored by a person")
    failing = [s for s in rescored if not _passes(criterion, s)]
    return (failing[0] if failing else rescored[0]), True


def _passes(criterion: Criterion, score: CriterionScore) -> bool:
    if score.state == "unknown":
        return False
    if criterion.kind == CriterionKind.MUST_PASS:
        return score.passed is True
    assert criterion.floor is not None
    return score.points is not None and score.points >= criterion.floor


def evaluate_rubric(
    *,
    rubric: ReviewRubric,
    scorecards: Sequence[RubricScorecard],
    subject: Subject,
    subject_text: str,
    created_at: datetime,
    block_texts: Mapping[str, str] | None = None,
    base_rubric: ReviewRubric | None = None,
    supported_bases: Sequence[RubricRef] | None = None,
) -> RubricEvaluation:
    blocks = block_texts or {}
    if not digest_is_current(rubric) or not all(digest_is_current(card) for card in scorecards):
        raise _refuse("a rubric or scorecard digest is stale")
    check_masthead_raises_only(rubric, base_rubric, supported_bases)

    primaries = [card for card in scorecards if card.overrides_ref is None]
    if len(primaries) != 1:
        raise _refuse("exactly one primary scorecard is required")
    primary = primaries[0]
    if len({card.scorecard_id for card in scorecards}) != len(scorecards):
        raise _refuse("scorecard identifiers must be unique")
    for card in scorecards:
        if card.rubric_ref != rubric.ref():
            raise _refuse("a scorecard pins a different rubric")
        if card.subject != subject:
            raise _refuse("a scorecard scores a different subject")
        if card.language != primary.language or card.language not in rubric.languages:
            raise _refuse("the subject's language is not one this rubric covers")
        if (card.organization_id, card.publication_id) != (
            rubric.organization_id,
            rubric.publication_id,
        ):
            raise _refuse("a scorecard belongs to a different publication scope")
        if card.overrides_ref is not None and card.overrides_ref != primary.ref():
            raise _refuse("a re-scoring must reference the primary scorecard it re-scores")
        known = {item.criterion_id for item in rubric.criteria}
        if any(given.criterion_id not in known for given in card.scores):
            raise _refuse("a scorecard scores a criterion the rubric does not have")
        for given in card.scores:
            _check_text(given, subject_text, blocks)

    findings: list[RubricFinding] = []
    overridden: list[str] = []
    weighted_points = weighted_max = 0
    for criterion in rubric.criteria:
        score, rescored = _effective(scorecards, primary, criterion)
        if criterion.kind == CriterionKind.SCORED:
            assert criterion.max_points is not None and criterion.weight is not None
            weighted_max += criterion.max_points * criterion.weight
        if score is None:
            findings.append(_finding(FindingKind.MISSING_SCORE, criterion, "no score was given"))
            continue
        if score.state == "unknown":
            findings.append(_finding(FindingKind.UNKNOWN_SCORE, criterion, score.reason, score))
            continue
        if criterion.kind == CriterionKind.MUST_PASS:
            if score.passed is None:
                raise _refuse("a must-pass criterion is scored pass or fail, not by points")
            if not score.passed:
                findings.append(
                    _finding(FindingKind.MUST_PASS_FAILED, criterion, score.reason, score)
                )
        else:
            assert criterion.max_points is not None and criterion.weight is not None
            assert criterion.floor is not None
            if score.points is None:
                raise _refuse("a scored criterion is scored by points, not pass or fail")
            if score.points > criterion.max_points:
                raise _refuse("points exceed the criterion's max_points")
            weighted_points += score.points * criterion.weight
            if score.points < criterion.floor:
                findings.append(_finding(FindingKind.BELOW_FLOOR, criterion, score.reason, score))
        if rescored and _passes(criterion, score):
            primary_score = next(
                (s for s in primary.scores if s.criterion_id == criterion.criterion_id), None
            )
            if primary_score is None or not _passes(criterion, primary_score):
                overridden.append(criterion.criterion_id)

    if rubric.aggregate_floor is not None and not _meets(
        rubric.aggregate_floor, weighted_points, weighted_max
    ):
        findings.append(
            RubricFinding(
                code=_FINDING_CODES[FindingKind.AGGREGATE_BELOW_FLOOR],
                kind=FindingKind.AGGREGATE_BELOW_FLOOR,
                reason="the weighted total is below the rubric's aggregate floor",
            )
        )

    refs = tuple(card.ref() for card in scorecards)
    return RubricEvaluation(
        created_at=created_at,
        organization_id=rubric.organization_id,
        publication_id=rubric.publication_id,
        input_refs=tuple(card.scorecard_id for card in scorecards),
        evaluation_id=stable_id(
            "rubric_eval",
            rubric.content_digest,
            canonical_digest(subject),
            *(r.digest for r in refs),
        ),
        rubric_ref=rubric.ref(),
        subject=subject,
        language=primary.language,
        scorecard_refs=refs,
        passed=not findings,
        weighted_points=weighted_points,
        weighted_max=weighted_max,
        overridden_criteria=tuple(overridden),
        findings=tuple(findings),
    )


def _finding(
    kind: FindingKind,
    criterion: Criterion,
    reason: str,
    score: CriterionScore | None = None,
) -> RubricFinding:
    evidence = score.evidence if score is not None else ()
    if score is not None and not evidence:
        raise _refuse("a failing or unknown score carries evidence")
    return RubricFinding(
        code=_FINDING_CODES[kind],
        kind=kind,
        criterion_id=criterion.criterion_id,
        rule_ref=criterion.rule_ref,
        reason=reason,
        evidence=evidence,
    )
