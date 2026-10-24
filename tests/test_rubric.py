"""The rubric engine applies any rubric, and a masthead can raise a floor but never lower it."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from zeo_creator.contracts.common import canonical_digest
from zeo_creator.contracts.rubric import (
    AggregateFloor,
    ArtifactRegion,
    CorpusMatch,
    Criterion,
    CriterionScore,
    FindingKind,
    ManifestSubject,
    MissingElement,
    ReviewRubric,
    RubricRef,
    RubricScorecard,
    TextQuote,
)
from zeo_creator.errors import CreatorDomainError
from zeo_creator.services.rubric import evaluate_rubric

NOW = datetime(2026, 10, 13, 12, 0, tzinfo=UTC)
DIGEST = "sha256:" + "a" * 64
SUBJECT = ManifestSubject(brief_id="b1", manifest_id="m1", content_digest=DIGEST)
TEXT = "The pilot skipped the receipt check. A second paragraph follows."


def scored(cid: str, floor: int = 3, weight: int = 1, **extra: object) -> Criterion:
    return Criterion(
        criterion_id=cid,
        kind="scored",
        rule_ref=f"rule.{cid}",
        guidance="g",
        max_points=5,
        floor=floor,
        weight=weight,
        **extra,  # type: ignore[arg-type]
    )


def must(cid: str) -> Criterion:
    return Criterion(criterion_id=cid, kind="must_pass", rule_ref=f"rule.{cid}", guidance="g")


def rubric(criteria: tuple[Criterion, ...] | None = None, **kw: object) -> ReviewRubric:
    base: dict[str, object] = dict(
        created_at=NOW,
        organization_id="org",
        publication_id="pub",
        rubric_id="house.note",
        rubric_version="1.0.0",
        medium="note",
        scope="house",
        languages=("en",),
        criteria=criteria or (scored("hook"), scored("clarity"), must("no-fabrication")),
    )
    base.update(kw)
    return ReviewRubric(**base)  # type: ignore[arg-type]


def evidence() -> tuple[TextQuote, ...]:
    return (TextQuote(quote="skipped the receipt check"),)


def card(
    rb: ReviewRubric,
    scores: dict[str, object],
    *,
    sid: str = "sc1",
    role: str = "agent",
    overrides: object = None,
    language: str = "en",
) -> RubricScorecard:
    items = []
    for cid, value in scores.items():
        if isinstance(value, CriterionScore):
            items.append(value)
        elif isinstance(value, bool):
            items.append(
                CriterionScore(
                    criterion_id=cid,
                    state="scored",
                    passed=value,
                    reason="r",
                    evidence=() if value else evidence(),
                )
            )
        else:
            assert isinstance(value, int)
            items.append(
                CriterionScore(
                    criterion_id=cid,
                    state="scored",
                    points=value,
                    reason="r",
                    evidence=() if value >= 3 else evidence(),
                )
            )
    return RubricScorecard(
        created_at=NOW,
        organization_id="org",
        publication_id="pub",
        scorecard_id=sid,
        rubric_ref=rb.ref(),
        subject=SUBJECT,
        language=language,
        reviewer_ref="reviewer",
        reviewer_role=role,
        human_participation_ref="ref" if role == "human" else None,
        overrides_ref=overrides,
        scores=tuple(items),  # type: ignore[arg-type]
    )


def run(rb: ReviewRubric, cards: list[RubricScorecard], **kw: object):
    return evaluate_rubric(
        rubric=rb,
        scorecards=cards,
        subject=SUBJECT,
        subject_text=TEXT,
        created_at=NOW,
        **kw,  # type: ignore[arg-type]
    )


GOOD = {"hook": 4, "clarity": 5, "no-fabrication": True}


def test_a_clean_scorecard_passes_and_reports_the_exact_total() -> None:
    rb = rubric()
    result = run(rb, [card(rb, GOOD)])
    assert result.passed and result.findings == ()
    assert (result.weighted_points, result.weighted_max) == (9, 10)


def test_below_a_floor_blocks_with_quoted_evidence() -> None:
    rb = rubric()
    result = run(rb, [card(rb, {**GOOD, "hook": 1})])
    assert not result.passed
    finding = result.findings[0]
    assert finding.kind == FindingKind.BELOW_FLOOR and finding.criterion_id == "hook"
    assert finding.rule_ref == "rule.hook" and finding.evidence == evidence()


def test_a_heavy_weight_on_a_strong_criterion_cannot_carry_a_floor_miss() -> None:
    rb = rubric((scored("strong", weight=100), scored("weak", weight=1), must("m")))
    result = run(rb, [card(rb, {"strong": 5, "weak": 1, "m": True})])
    assert result.weighted_points / result.weighted_max > 0.95  # the average is excellent
    assert not result.passed and result.findings[0].criterion_id == "weak"


def test_a_failed_must_pass_blocks_whatever_the_points() -> None:
    rb = rubric()
    result = run(rb, [card(rb, {**GOOD, "no-fabrication": False})])
    assert not result.passed and result.findings[0].kind == FindingKind.MUST_PASS_FAILED


def test_unknown_and_missing_scores_fail_closed() -> None:
    rb = rubric()
    unknown = CriterionScore(
        criterion_id="hook",
        state="unknown",
        reason="no corpus",
        evidence=(MissingElement(element_id="corpus"),),
    )
    result = run(rb, [card(rb, {"hook": unknown, "clarity": 5, "no-fabrication": True})])
    assert result.findings[0].kind == FindingKind.UNKNOWN_SCORE
    partial = run(rb, [card(rb, {"hook": 5, "no-fabrication": True})])
    assert partial.findings[0].kind == FindingKind.MISSING_SCORE


def test_a_failing_score_without_evidence_is_refused_not_passed() -> None:
    rb = rubric()
    bare = CriterionScore(criterion_id="hook", state="scored", points=1, reason="weak")
    with pytest.raises(CreatorDomainError, match="evidence"):
        run(rb, [card(rb, {"hook": bare, "clarity": 5, "no-fabrication": True})])


def test_a_quote_must_occur_in_the_subjects_text_or_named_block() -> None:
    rb = rubric()
    fake = CriterionScore(
        criterion_id="hook",
        state="scored",
        points=1,
        reason="r",
        evidence=(TextQuote(quote="never said this"),),
    )
    with pytest.raises(CreatorDomainError, match="quoted passage"):
        run(rb, [card(rb, {"hook": fake, "clarity": 5, "no-fabrication": True})])
    blocked = CriterionScore(
        criterion_id="hook",
        state="scored",
        points=1,
        reason="r",
        evidence=(TextQuote(quote="in block", block_id="b2"),),
    )
    result = run(
        rb,
        [card(rb, {"hook": blocked, "clarity": 5, "no-fabrication": True})],
        block_texts={"b2": "text in block two"},
    )
    assert not result.passed


def test_non_text_evidence_needs_no_quote() -> None:
    rb = rubric()
    for item in (
        ArtifactRegion(artifact_ref="slide-3", region="x=10,y=20,w=40,h=30"),
        CorpusMatch(matched_manifest_id="m0", matched_digest=DIGEST, corpus_snapshot_digest=DIGEST),
    ):
        score = CriterionScore(
            criterion_id="hook", state="scored", points=0, reason="r", evidence=(item,)
        )
        result = run(rb, [card(rb, {"hook": score, "clarity": 5, "no-fabrication": True})])
        assert result.findings[0].evidence == (item,)


def test_the_aggregate_floor_is_exact_and_half_up_percent_rounds_as_declared() -> None:
    exact = rubric(aggregate_floor=AggregateFloor(numerator=9, denominator=10))
    assert run(exact, [card(exact, GOOD)]).passed  # 9/10 meets 9/10
    higher = rubric(aggregate_floor=AggregateFloor(numerator=91, denominator=100))
    result = run(higher, [card(higher, GOOD)])
    assert result.findings[0].kind == FindingKind.AGGREGATE_BELOW_FLOOR
    legacy = rubric(
        aggregate_floor=AggregateFloor(numerator=70, denominator=100, rounding="half_up_percent")
    )
    seven = {"hook": 3, "clarity": 4, "no-fabrication": True}  # 7/10 = 70%
    assert run(legacy, [card(legacy, seven)]).passed
    edge = rubric(
        (scored("a", floor=0), scored("b", floor=0), must("m")),
        aggregate_floor=AggregateFloor(numerator=50, denominator=100, rounding="half_up_percent"),
    )
    # 4.95/10 would round half up to 50%: here 5/10 is exactly 50%.
    assert run(edge, [card(edge, {"a": 5, "b": 0, "m": True})]).passed


def test_language_is_checked() -> None:
    rb = rubric()
    with pytest.raises(CreatorDomainError, match="language"):
        run(rb, [card(rb, GOOD, language="es")])


def test_stale_or_foreign_inputs_are_refused() -> None:
    rb, other = rubric(), rubric(rubric_version="2.0.0")
    with pytest.raises(CreatorDomainError, match="different rubric"):
        run(rb, [card(other, GOOD)])
    tampered = card(rb, GOOD).model_copy(update={"reviewer_ref": "someone-else"})
    with pytest.raises(CreatorDomainError, match="stale"):
        run(rb, [tampered])


def test_a_human_rescoring_overrides_only_as_a_separate_recorded_scorecard() -> None:
    rb = rubric()
    agent = card(rb, {**GOOD, "hook": 1})
    human = card(rb, {"hook": 4}, sid="sc2", role="human", overrides=agent.ref())
    result = run(rb, [agent, human])
    assert result.passed and result.overridden_criteria == ("hook",)
    assert {r.scorecard_id for r in result.scorecard_refs} == {"sc1", "sc2"}


def test_a_human_rescoring_still_meets_the_floor_and_a_human_failure_stands() -> None:
    rb = rubric()
    agent = card(rb, {**GOOD, "hook": 1})
    still_low = card(rb, {"hook": 2}, sid="sc2", role="human", overrides=agent.ref())
    assert not run(rb, [agent, still_low]).passed
    passing_agent = card(rb, GOOD)
    human_fail = card(rb, {"hook": 0}, sid="sc2", role="human", overrides=passing_agent.ref())
    assert not run(rb, [passing_agent, human_fail]).passed


def test_a_producer_backed_criterion_cannot_be_rescored_by_a_person() -> None:
    rb = rubric((scored("unique", backing_check_id="producer.uniqueness"), scored("x"), must("m")))
    agent = card(rb, {"unique": 1, "x": 5, "m": True})
    human = card(rb, {"unique": 5}, sid="sc2", role="human", overrides=agent.ref())
    with pytest.raises(CreatorDomainError, match="producer check"):
        run(rb, [agent, human])


def test_rescoring_must_reference_the_primary_scorecard() -> None:
    rb = rubric()
    agent = card(rb, GOOD)
    stray = card(
        rb, {"hook": 5}, sid="sc2", role="human", overrides=card(rb, GOOD, sid="other").ref()
    )
    with pytest.raises(CreatorDomainError, match="re-scoring"):
        run(rb, [agent, stray])


def test_contract_shapes_are_strict() -> None:
    with pytest.raises(ValidationError, match="masthead rubric must name"):
        rubric(scope="masthead")
    with pytest.raises(ValidationError, match="no points"):
        Criterion(criterion_id="m", kind="must_pass", rule_ref="r", guidance="g", max_points=3)
    with pytest.raises(ValidationError, match="floor cannot exceed"):
        scored("x", floor=9)
    with pytest.raises(ValidationError, match="unique"):
        rubric((scored("a"), scored("a")))
    with pytest.raises(ValidationError, match="evidence of what"):
        CriterionScore(criterion_id="a", state="unknown", reason="r")
    with pytest.raises(ValidationError, match="human participation"):
        RubricScorecard(
            created_at=NOW,
            organization_id="o",
            publication_id="p",
            scorecard_id="s",
            rubric_ref=rubric().ref(),
            subject=SUBJECT,
            language="en",
            reviewer_ref="r",
            reviewer_role="human",
            scores=(CriterionScore(criterion_id="a", state="scored", points=1, reason="r"),),
        )
    assert canonical_digest(rubric()) == rubric().content_digest


# --- raise, never lower (D1): one failing test for each way a masthead could lower a floor ---


def house() -> ReviewRubric:
    return rubric(aggregate_floor=AggregateFloor(numerator=6, denominator=10))


def masthead(criteria: tuple[Criterion, ...] | None = None, **kw: object) -> ReviewRubric:
    base = house()
    return rubric(
        criteria or (scored("hook"), scored("clarity"), must("no-fabrication")),
        scope="masthead",
        rubric_id="masthead.note",
        base_rubric_ref=base.ref(),
        aggregate_floor=kw.pop("aggregate_floor", AggregateFloor(numerator=6, denominator=10)),
        **kw,
    )


def run_masthead(rb: ReviewRubric, **kw: object) -> object:
    base = kw.pop("base", house())
    supported = kw.pop("supported", [house().ref()])
    return run(rb, [card(rb, GOOD)], base_rubric=base, supported_bases=supported)


def test_a_masthead_that_only_raises_floors_is_accepted() -> None:
    rb = masthead(
        (scored("hook", floor=4), scored("clarity"), must("no-fabrication")),
        aggregate_floor=AggregateFloor(numerator=7, denominator=10),
    )
    assert run_masthead(rb).passed  # type: ignore[attr-defined]


def test_refuses_a_missing_base_criterion() -> None:
    with pytest.raises(CreatorDomainError, match="criterion is missing"):
        run_masthead(masthead((scored("hook"), must("no-fabrication"))))


def producer_house() -> ReviewRubric:
    return rubric(
        (scored("unique", backing_check_id="producer.uniqueness"), scored("x"), must("m")),
        aggregate_floor=AggregateFloor(numerator=6, denominator=10),
    )


def producer_masthead(unique: Criterion) -> ReviewRubric:
    base = producer_house()
    return rubric(
        (unique, scored("x"), must("m")),
        scope="masthead",
        rubric_id="masthead.note",
        base_rubric_ref=base.ref(),
        aggregate_floor=AggregateFloor(numerator=6, denominator=10),
    )


def run_producer_masthead(rb: ReviewRubric, *cards: RubricScorecard) -> object:
    return run(
        rb, list(cards), base_rubric=producer_house(), supported_bases=[producer_house().ref()]
    )


@pytest.mark.parametrize("binding", [None, "producer.other"])
def test_refuses_a_masthead_that_drops_or_rebinds_a_producer_check(binding: str | None) -> None:
    rb = producer_masthead(scored("unique", backing_check_id=binding))
    agent = card(rb, {"unique": 1, "x": 5, "m": True})
    human = card(rb, {"unique": 5}, sid="sc2", role="human", overrides=agent.ref())
    with pytest.raises(CreatorDomainError, match="producer check was removed or rebound"):
        run_producer_masthead(rb, agent, human)


def test_a_masthead_keeping_the_producer_check_still_forbids_human_rescoring() -> None:
    rb = producer_masthead(scored("unique", backing_check_id="producer.uniqueness"))
    agent = card(rb, {"unique": 1, "x": 5, "m": True})
    human = card(rb, {"unique": 5}, sid="sc2", role="human", overrides=agent.ref())
    with pytest.raises(CreatorDomainError, match="backed by a producer check"):
        run_producer_masthead(rb, agent, human)


def test_a_masthead_may_rescore_a_non_producer_criterion_by_a_person() -> None:
    rb = producer_masthead(scored("unique", backing_check_id="producer.uniqueness"))
    agent = card(rb, {"unique": 5, "x": 1, "m": True})
    human = card(rb, {"x": 5}, sid="sc2", role="human", overrides=agent.ref())
    assert run_producer_masthead(rb, agent, human).passed  # type: ignore[attr-defined]


def test_refuses_a_lower_criterion_floor() -> None:
    with pytest.raises(CreatorDomainError, match="floor is lower"):
        run_masthead(masthead((scored("hook", floor=2), scored("clarity"), must("no-fabrication"))))


def test_refuses_a_different_max_points() -> None:
    changed = Criterion(
        criterion_id="hook",
        kind="scored",
        rule_ref="rule.hook",
        guidance="g",
        max_points=10,
        floor=3,
        weight=1,
    )
    with pytest.raises(CreatorDomainError, match="max_points differs"):
        run_masthead(masthead((changed, scored("clarity"), must("no-fabrication"))))


def test_refuses_a_must_pass_made_scored_or_dropped() -> None:
    with pytest.raises(CreatorDomainError, match="changed kind"):
        run_masthead(masthead((scored("hook"), scored("clarity"), scored("no-fabrication"))))
    with pytest.raises(CreatorDomainError, match="criterion is missing"):
        run_masthead(masthead((scored("hook"), scored("clarity"))))


def test_refuses_a_lower_aggregate_floor_or_a_missing_one() -> None:
    with pytest.raises(CreatorDomainError, match="aggregate floor is lower"):
        run_masthead(masthead(aggregate_floor=AggregateFloor(numerator=5, denominator=10)))
    with pytest.raises(CreatorDomainError, match="aggregate floor is missing"):
        run_masthead(masthead(aggregate_floor=None))


def test_refuses_a_rounding_that_could_hide_a_lower_floor() -> None:
    legacy = AggregateFloor(numerator=60, denominator=100, rounding="half_up_percent")
    with pytest.raises(CreatorDomainError, match="different rounding"):
        run_masthead(masthead(aggregate_floor=legacy))


def test_refuses_a_missing_or_mismatched_base() -> None:
    rb = masthead()
    with pytest.raises(CreatorDomainError, match="missing or does not match"):
        run_masthead(rb, base=None)
    other_base = rubric(rubric_version="1.0.0", languages=("en", "es"))
    with pytest.raises(CreatorDomainError, match="missing or does not match"):
        run_masthead(rb, base=other_base)


def test_refuses_a_base_the_house_does_not_list_as_supported() -> None:
    rb = masthead()
    with pytest.raises(CreatorDomainError, match="supported"):
        run_masthead(
            rb, supported=[RubricRef(rubric_id="house.note", rubric_version="0.9.0", digest=DIGEST)]
        )
    with pytest.raises(CreatorDomainError, match="supported"):
        run_masthead(rb, supported=None)


def test_a_changed_weight_must_be_declared() -> None:
    reweighted = (scored("hook", weight=3), scored("clarity"), must("no-fabrication"))
    with pytest.raises(CreatorDomainError, match="weight is not declared"):
        run_masthead(masthead(reweighted))
    assert run_masthead(masthead(reweighted, declared_weight_changes=("hook",))).passed  # type: ignore[attr-defined]


def test_an_added_scored_criterion_must_be_declared() -> None:
    padded = (
        scored("hook"),
        scored("clarity"),
        must("no-fabrication"),
        scored("pad", floor=0, weight=98),
    )
    with pytest.raises(CreatorDomainError, match="added scored criterion is not declared"):
        run_masthead(masthead(padded))


def test_a_declared_added_scored_criterion_is_accepted() -> None:
    added = (scored("hook"), scored("clarity"), must("no-fabrication"), scored("voice"))
    rb = masthead(added, declared_weight_changes=("voice",))
    result = evaluate_rubric(
        rubric=rb,
        scorecards=[card(rb, {**GOOD, "voice": 4})],
        subject=SUBJECT,
        subject_text=TEXT,
        created_at=NOW,
        base_rubric=house(),
        supported_bases=[house().ref()],
    )
    assert result.passed


def test_an_added_must_pass_criterion_needs_no_declaration() -> None:
    added = (scored("hook"), scored("clarity"), must("no-fabrication"), must("no-spam"))
    rb = masthead(added)
    result = evaluate_rubric(
        rubric=rb,
        scorecards=[card(rb, {**GOOD, "no-spam": True})],
        subject=SUBJECT,
        subject_text=TEXT,
        created_at=NOW,
        base_rubric=house(),
        supported_bases=[house().ref()],
    )
    assert result.passed


def test_points_above_max_points_are_refused() -> None:
    rb = rubric()
    with pytest.raises(CreatorDomainError, match="exceed"):
        run(rb, [card(rb, {**GOOD, "hook": 6})])
