"""Medium-agnostic scored review rubrics, scorecards and their evaluation.

A rubric is data: criteria with floors and weights. Creator ships the shape and the pure
engine that applies any rubric; it holds no rubric instance, scorer, lexicon, persona or
profile. Points and weights are integers, so every digest and ratio is exact.
"""

from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from zeo_creator.contracts.common import CreatorModel, DurableArtifact
from zeo_creator.contracts.editorial import ContentKind

CRITERION_ID = r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$"
SEMVER = r"^\d+\.\d+\.\d+$"
DIGEST = r"^sha256:[0-9a-f]{64}$"
LANGUAGE = r"^[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})*$"

CriterionId = Annotated[str, Field(pattern=CRITERION_ID, max_length=96)]
Digest = Annotated[str, Field(pattern=DIGEST)]
Language = Annotated[str, Field(pattern=LANGUAGE)]


class CriterionKind(StrEnum):
    SCORED = "scored"
    MUST_PASS = "must_pass"


class RubricScope(StrEnum):
    HOUSE = "house"
    MASTHEAD = "masthead"


class Rounding(StrEnum):
    EXACT = "exact"
    HALF_UP_PERCENT = "half_up_percent"


class Criterion(CreatorModel):
    criterion_id: CriterionId
    kind: CriterionKind
    rule_ref: str = Field(min_length=1)
    guidance: str = Field(min_length=1)
    max_points: int | None = Field(default=None, ge=1)
    floor: int | None = Field(default=None, ge=0)
    weight: int | None = Field(default=None, ge=1)
    backing_check_id: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def shape_matches_kind(self) -> Self:
        scored = (self.max_points, self.floor, self.weight)
        if self.kind == CriterionKind.SCORED:
            if any(item is None for item in scored):
                raise ValueError("a scored criterion needs max_points, floor and weight")
            if self.floor is not None and self.max_points is not None:
                if self.floor > self.max_points:
                    raise ValueError("a floor cannot exceed max_points")
        elif any(item is not None for item in scored):
            raise ValueError("a must_pass criterion carries no points, floor or weight")
        return self


class AggregateFloor(CreatorModel):
    """The weighted ratio must reach numerator/denominator, compared under one rounding."""

    numerator: int = Field(ge=0)
    denominator: int = Field(ge=1)
    rounding: Rounding = Rounding.EXACT

    @model_validator(mode="after")
    def percent_rounding_is_whole_percent(self) -> Self:
        if self.numerator > self.denominator:
            raise ValueError("an aggregate floor cannot exceed one")
        if self.rounding == Rounding.HALF_UP_PERCENT and self.denominator != 100:
            raise ValueError("half_up_percent rounding compares whole percent over 100")
        return self


class RubricRef(CreatorModel):
    rubric_id: CriterionId
    rubric_version: Annotated[str, Field(pattern=SEMVER)]
    digest: Digest


class ReviewRubric(DurableArtifact):
    rubric_id: CriterionId
    rubric_version: Annotated[str, Field(pattern=SEMVER)]
    medium: ContentKind
    scope: RubricScope
    languages: tuple[Language, ...] = Field(min_length=1)
    criteria: tuple[Criterion, ...] = Field(min_length=1)
    aggregate_floor: AggregateFloor | None = None
    base_rubric_ref: RubricRef | None = None
    declared_weight_changes: tuple[CriterionId, ...] = ()

    @model_validator(mode="after")
    def coherent_rubric(self) -> Self:
        ids = [item.criterion_id for item in self.criteria]
        if len(ids) != len(set(ids)):
            raise ValueError("criterion identifiers must be unique")
        if len(self.languages) != len(set(self.languages)):
            raise ValueError("languages must be unique")
        if self.scope == RubricScope.MASTHEAD and self.base_rubric_ref is None:
            raise ValueError("a masthead rubric must name the house rubric it builds on")
        if self.aggregate_floor is not None and not any(
            item.kind == CriterionKind.SCORED for item in self.criteria
        ):
            raise ValueError("an aggregate floor needs at least one scored criterion")
        if any(item not in ids for item in self.declared_weight_changes):
            raise ValueError("a declared weight change must name a criterion of this rubric")
        if self.base_rubric_ref is None and self.declared_weight_changes:
            raise ValueError("weight changes are declared against a base rubric")
        return self

    def ref(self) -> RubricRef:
        return RubricRef(
            rubric_id=self.rubric_id,
            rubric_version=self.rubric_version,
            digest=self.content_digest,
        )


class TextQuote(CreatorModel):
    kind: Literal["text_quote"] = "text_quote"
    quote: str = Field(min_length=1)
    block_id: str | None = Field(default=None, min_length=1)


class ArtifactRegion(CreatorModel):
    kind: Literal["artifact_region"] = "artifact_region"
    artifact_ref: str = Field(min_length=1)
    region: str = Field(min_length=1)


class MissingElement(CreatorModel):
    kind: Literal["missing_element"] = "missing_element"
    element_id: str = Field(min_length=1)


class CorpusMatch(CreatorModel):
    kind: Literal["corpus_match"] = "corpus_match"
    matched_manifest_id: str = Field(min_length=1)
    matched_digest: Digest
    corpus_snapshot_digest: Digest


Evidence = Annotated[
    TextQuote | ArtifactRegion | MissingElement | CorpusMatch, Field(discriminator="kind")
]


class ManifestSubject(CreatorModel):
    kind: Literal["manifest"] = "manifest"
    brief_id: str = Field(min_length=1)
    manifest_id: str = Field(min_length=1)
    content_digest: Digest


class DocumentSubject(CreatorModel):
    kind: Literal["document"] = "document"
    document_id: str = Field(min_length=1)
    source_revision: str = Field(min_length=1)
    source_digest: Digest


Subject = Annotated[ManifestSubject | DocumentSubject, Field(discriminator="kind")]


class CriterionScore(CreatorModel):
    criterion_id: CriterionId
    state: Literal["scored", "unknown"]
    points: int | None = Field(default=None, ge=0)
    passed: bool | None = None
    reason: str = Field(min_length=1)
    evidence: tuple[Evidence, ...] = ()

    @model_validator(mode="after")
    def state_matches_values(self) -> Self:
        if self.state == "scored":
            if (self.points is None) == (self.passed is None):
                raise ValueError("a scored criterion has exactly one of points and passed")
        else:
            if self.points is not None or self.passed is not None:
                raise ValueError("an unknown score carries neither points nor a pass")
            if not self.evidence:
                raise ValueError("an unknown score carries evidence of what could not be assessed")
        return self


class ScorecardRef(CreatorModel):
    scorecard_id: str = Field(min_length=1)
    digest: Digest


class RubricScorecard(DurableArtifact):
    scorecard_id: str = Field(min_length=1)
    rubric_ref: RubricRef
    subject: Subject
    language: Language
    reviewer_ref: str = Field(min_length=1)
    reviewer_role: Literal["agent", "human"]
    human_participation_ref: str | None = Field(default=None, min_length=1)
    overrides_ref: ScorecardRef | None = None
    scores: tuple[CriterionScore, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def coherent_scorecard(self) -> Self:
        ids = [item.criterion_id for item in self.scores]
        if len(ids) != len(set(ids)):
            raise ValueError("a scorecard scores each criterion once")
        if self.reviewer_role == "human" and self.human_participation_ref is None:
            raise ValueError("a human scorecard carries a human participation reference")
        if self.reviewer_role == "agent" and self.human_participation_ref is not None:
            raise ValueError("an agent scorecard carries no human participation reference")
        if self.overrides_ref is not None and self.reviewer_role != "human":
            raise ValueError("only a human scorecard re-scores another scorecard")
        return self

    def ref(self) -> ScorecardRef:
        return ScorecardRef(scorecard_id=self.scorecard_id, digest=self.content_digest)


class FindingKind(StrEnum):
    BELOW_FLOOR = "below_floor"
    MUST_PASS_FAILED = "must_pass_failed"
    UNKNOWN_SCORE = "unknown_score"
    MISSING_SCORE = "missing_score"
    AGGREGATE_BELOW_FLOOR = "aggregate_below_floor"


class RubricFinding(CreatorModel):
    code: Annotated[str, Field(pattern=r"^ZEO_CREATOR_[A-Z0-9_]+$")]
    kind: FindingKind
    severity: Literal["blocking"] = "blocking"
    criterion_id: CriterionId | None = None
    rule_ref: str | None = None
    reason: str = Field(min_length=1)
    evidence: tuple[Evidence, ...] = ()


class RubricEvaluation(DurableArtifact):
    evaluation_id: str = Field(min_length=1)
    rubric_ref: RubricRef
    subject: Subject
    language: Language
    scorecard_refs: tuple[ScorecardRef, ...] = Field(min_length=1)
    passed: bool
    weighted_points: int = Field(ge=0)
    weighted_max: int = Field(ge=0)
    overridden_criteria: tuple[CriterionId, ...] = ()
    findings: tuple[RubricFinding, ...] = ()

    @model_validator(mode="after")
    def passed_means_no_findings(self) -> Self:
        if self.passed == bool(self.findings):
            raise ValueError("an evaluation passes exactly when it has no blocking finding")
        return self
