"""Export deterministic schemas and credential-free neutral reference artifacts."""

import json
from pathlib import Path
from typing import Any

from tests.fixtures.reference import (
    build_reference_snapshot,
    evidence_fixture,
    recent_history,
)
from zeo_creator.capabilities._newsroom_examples import agenda, dossier, observation, signal, story
from zeo_creator.capabilities._specialization_examples import (
    article_draft,
    article_plan,
    commentary_draft,
    conversation,
    edition,
    newsletter_draft,
    newsletter_plan,
    opportunity,
)
from zeo_creator.contracts.commentary import (
    CommentaryDraft,
    CommentaryReview,
    ConversationObservation,
    EngagementOpportunity,
)
from zeo_creator.contracts.common import canonical_digest
from zeo_creator.contracts.delivery import ArtifactManifest, DeliveryReviewBundle
from zeo_creator.contracts.distribution import (
    ChannelPlan,
    DistributionVariant,
    ProposedPublicationOperation,
    PublicationReceipt,
)
from zeo_creator.contracts.editorial import ContentPortfolioPlan, EditorialAssignment
from zeo_creator.contracts.evidence import EvidenceItem, ResearchSynthesis
from zeo_creator.contracts.journalism import (
    CorrectionNotice,
    EditorialReview,
    NewsArticleDraft,
    NewsArticlePlan,
    PublicationUpdate,
    RetractionNotice,
)
from zeo_creator.contracts.newsletter import (
    AudienceSelection,
    NewsletterEditorialReview,
    NewsletterIssueDraft,
    NewsletterIssuePlan,
)
from zeo_creator.contracts.newsroom import (
    EditionPlan,
    EditorialAgenda,
    EditorialSignal,
    PublicationSlot,
    SourceObservation,
    StoryDossier,
    StoryRevision,
)
from zeo_creator.contracts.performance import MetricObservation, PerformanceAssessment
from zeo_creator.contracts.production import ContentBrief
from zeo_creator.contracts.publications import PublicationProfile
from zeo_creator.contracts.rubric import ReviewRubric, RubricEvaluation, RubricScorecard
from zeo_creator.registry import CAPABILITIES

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "reference"
PACKAGED_SCHEMAS = ROOT / "src" / "zeo_creator" / "schemas"


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def export_schemas() -> None:
    for root in (REFERENCE / "schemas", PACKAGED_SCHEMAS):
        root.mkdir(parents=True, exist_ok=True)
        for existing in root.glob("*.json"):
            existing.unlink()
    contract_models = (
        ("publication-profile", "1", PublicationProfile),
        ("evidence-item", "1", EvidenceItem),
        ("research-synthesis", "1", ResearchSynthesis),
        ("editorial-assignment", "1", EditorialAssignment),
        ("content-portfolio-plan", "1", ContentPortfolioPlan),
        ("content-brief", "1", ContentBrief),
        ("artifact-manifest", "1", ArtifactManifest),
        ("delivery-review-bundle", "1", DeliveryReviewBundle),
        ("review-rubric", "1", ReviewRubric),
        ("rubric-scorecard", "1", RubricScorecard),
        ("rubric-evaluation", "1", RubricEvaluation),
        ("distribution-variant", "1", DistributionVariant),
        ("channel-plan", "1", ChannelPlan),
        ("proposed-publication-operation", "1", ProposedPublicationOperation),
        ("publication-receipt", "1", PublicationReceipt),
        ("metric-observation", "1", MetricObservation),
        ("performance-assessment", "1", PerformanceAssessment),
        ("source-observation", "1", SourceObservation),
        ("editorial-signal", "1", EditorialSignal),
        ("story-revision", "1", StoryRevision),
        ("story-dossier", "1", StoryDossier),
        ("publication-slot", "1", PublicationSlot),
        ("editorial-agenda", "1", EditorialAgenda),
        ("edition-plan", "1", EditionPlan),
        ("conversation-observation", "1", ConversationObservation),
        ("engagement-opportunity", "1", EngagementOpportunity),
        ("commentary-draft", "1", CommentaryDraft),
        ("commentary-review", "1", CommentaryReview),
        ("audience-selection", "1", AudienceSelection),
        ("newsletter-issue-plan", "1", NewsletterIssuePlan),
        ("newsletter-issue-draft", "1", NewsletterIssueDraft),
        ("newsletter-editorial-review", "1", NewsletterEditorialReview),
        ("news-article-plan", "1", NewsArticlePlan),
        ("news-article-draft", "1", NewsArticleDraft),
        ("editorial-review", "1", EditorialReview),
        ("correction-notice", "1", CorrectionNotice),
        ("retraction-notice", "1", RetractionNotice),
        ("publication-update", "1", PublicationUpdate),
    )
    catalog = []
    for name, version, model in contract_models:
        filename = f"{name}.v{version}.schema.json"
        schema = model.model_json_schema()
        _write(REFERENCE / "schemas" / filename, schema)
        _write(PACKAGED_SCHEMAS / filename, schema)
        catalog.append(
            {
                "name": name,
                "version": version,
                "filename": filename,
                "schema_digest": canonical_digest(schema),
            }
        )
    _write(PACKAGED_SCHEMAS / "catalog.json", {"contracts": catalog})
    for capability in CAPABILITIES:
        name = capability.definition.projection_name
        _write(
            REFERENCE / "schemas" / f"{name}.request.schema.json",
            capability.request_model.model_json_schema(),
        )
        _write(
            REFERENCE / "schemas" / f"{name}.response.schema.json",
            capability.definition.response_schema,
        )


def export_examples() -> None:
    snapshot = build_reference_snapshot()
    evidence_by_query, _ = evidence_fixture()
    values = {
        "publication-profiles.json": snapshot.profiles,
        "evidence.json": tuple(item for rows in evidence_by_query.values() for item in rows),
        "recent-content-history.json": recent_history(),
        "content-portfolio-plan.json": snapshot.plan,
        "content-briefs.json": snapshot.briefs,
        "artifact-manifests.json": snapshot.manifests,
        "delivery-reviews.json": snapshot.reviews,
        "publication-proposals.json": snapshot.operations,
        "performance-assessments.json": snapshot.assessments,
        "editorial-kernel.json": (
            observation(),
            signal(),
            story(),
            dossier(),
            agenda(),
            edition(),
        ),
        "commentary.json": (conversation(), opportunity(), commentary_draft()),
        "newsletter.json": (newsletter_plan(), newsletter_draft()),
        "journalism.json": (article_plan(), article_draft()),
    }
    for filename, value in values.items():
        if isinstance(value, tuple):
            payload = [item.model_dump(mode="json") for item in value]
        else:
            payload = value.model_dump(mode="json")
        _write(REFERENCE / "examples" / filename, payload)


if __name__ == "__main__":
    export_schemas()
    export_examples()
