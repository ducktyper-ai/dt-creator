"""Version 4 email marketing artifacts. Intent and evidence confer no effect authority.

All references are opaque, scoped and digest-bound. Subscriber records and provider
payloads have no representation. Runtime owns reference resolution and authorization.
"""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Annotated, Literal, Self
from urllib.parse import parse_qsl, urlsplit

from pydantic import BaseModel, ConfigDict, Field, model_validator
from zeo_core.contracts import CapabilityId

from zeo_creator.contracts.common import (
    CreatorModel,
    DurableArtifact,
    UtcDatetime,
    canonical_digest,
)
from zeo_creator.contracts.evidence import ResearchWindow
from zeo_creator.contracts.newsroom import GenerationTrace

Digest = Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
OpaqueRef = Annotated[str, Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_.:/-]{0,199}$")]
Text = Annotated[str, Field(min_length=1, max_length=20000)]


def _no_addresses(value: object) -> None:
    if isinstance(value, BaseModel):
        _no_addresses(value.model_dump(mode="json"))
    elif isinstance(value, dict):
        for child in value.values():
            _no_addresses(child)
    elif isinstance(value, (tuple, list)):
        for child in value:
            _no_addresses(child)
    elif isinstance(value, str) and re.search(r"[^\s<>@]+@[^\s<>@]+\.[a-zA-Z]{2,}", value):
        raise ValueError("email addresses are not accepted in email marketing artifacts")


class EmailModel(CreatorModel):
    model_config = ConfigDict(
        hide_input_in_errors=True, revalidate_instances="always", str_strip_whitespace=False
    )

    @model_validator(mode="after")
    def no_contact_addresses(self) -> Self:
        _no_addresses(self)
        return self


class ScopedEmailModel(EmailModel):
    organization_id: OpaqueRef
    publication_id: OpaqueRef

    @model_validator(mode="after")
    def nested_scope_matches(self) -> Self:
        def walk(item: object) -> None:
            if isinstance(item, BaseModel):
                org = getattr(item, "organization_id", self.organization_id)
                pub = getattr(item, "publication_id", self.publication_id)
                if (org, pub) != (self.organization_id, self.publication_id):
                    raise ValueError("email artifact publication scope mismatch")
                for key in type(item).model_fields:
                    walk(getattr(item, key))
            elif isinstance(item, (tuple, list)):
                for child in item:
                    walk(child)

        for key in type(self).model_fields:
            walk(getattr(self, key))
        return self


class EmailArtifact(ScopedEmailModel, DurableArtifact):
    model_config = ConfigDict(str_strip_whitespace=False)

    schema_version: Literal["4.0.0"] = "4.0.0"
    artifact_id: OpaqueRef

    def binding(self) -> EmailArtifactRef:
        return EmailArtifactRef(
            organization_id=self.organization_id,
            publication_id=self.publication_id,
            ref=self.artifact_id,
            revision=self.revision,
            digest=self.content_digest,
        )


class EmailArtifactRef(ScopedEmailModel):
    ref: OpaqueRef
    revision: int = Field(ge=1)
    digest: Digest


class AudienceIntent(ScopedEmailModel):
    segment_refs: tuple[OpaqueRef, ...] = Field(min_length=1)
    lifecycle_states: tuple[OpaqueRef, ...] = ()
    required_inclusions: tuple[OpaqueRef, ...] = ()
    required_exclusions: tuple[OpaqueRef, ...] = ()
    consent_policy: EmailArtifactRef | None
    suppression_policy: EmailArtifactRef | None
    jurisdiction_policies: tuple[EmailArtifactRef, ...] = ()
    frequency_cap_policy: EmailArtifactRef
    purpose_of_contact: Text
    cross_publication_use_policy: EmailArtifactRef

    @model_validator(mode="after")
    def audience_sets(self) -> Self:
        for items in (self.segment_refs, self.required_inclusions, self.required_exclusions):
            if len(items) != len(set(items)):
                raise ValueError("audience references must be unique")
        if set(self.required_inclusions) & set(self.required_exclusions):
            raise ValueError("audience inclusions and exclusions overlap")
        return self


class AudienceSnapshotSummary(ScopedEmailModel):
    snapshot_ref: OpaqueRef
    snapshot_digest: Digest
    provider_kind: OpaqueRef
    connection_ref: OpaqueRef
    audience_intent_digest: Digest
    eligible_count: int = Field(ge=0)
    suppressed_count: int = Field(ge=0)
    resolved_at: UtcDatetime
    expires_at: UtcDatetime
    segment_definition_digest: Digest
    consent_policy_digest: Digest
    suppression_policy_digest: Digest
    drift_status: Literal["unchanged", "changed", "unknown"]
    purpose: Literal["production", "test"]

    @model_validator(mode="after")
    def valid_window(self) -> Self:
        if self.expires_at <= self.resolved_at:
            raise ValueError("snapshot expiry must follow resolution")
        return self


class EmailCTA(EmailModel):
    cta_id: OpaqueRef
    link_id: OpaqueRef
    label: Text
    desired_action: Text
    primary: bool = False


def exact_ctas(rows: tuple[EmailCTA, ...]) -> dict[str, EmailCTA]:
    if len({row.cta_id for row in rows}) != len(rows):
        raise ValueError("CTA identities must be unique")
    if len({row.link_id for row in rows}) != len(rows):
        raise ValueError("CTA link identities must be unique")
    if sum(row.primary for row in rows) != 1:
        raise ValueError("CTA plan requires exactly one primary CTA")
    return {row.cta_id: row for row in rows}


def check_public_link(url: str) -> None:
    """Refuse anything but an absolute HTTPS URL without userinfo, templating or tracking."""
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or "{" in url
        or "}" in url
        # Browsers read a backslash as a path separator that urlsplit does not, so a
        # host like "evil.example\@trusted.example" would display one site and open another.
        or "\\" in url
    ):
        raise ValueError("links require absolute HTTPS URLs without userinfo or tracking values")
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        if (
            key.casefold().startswith(("utm_", "mc_", "hs", "email", "contact", "subscriber"))
            or key.casefold() in {"fbclid", "gclid"}
            or "@" in value
        ):
            raise ValueError("links must not carry tracking or subscriber parameters")


class EmailLink(EmailModel):
    link_id: OpaqueRef
    url: Annotated[str, Field(min_length=1, max_length=2048)]
    purpose: Literal["content", "cta", "unsubscribe"]
    tracking_required: bool

    @model_validator(mode="after")
    def public_link(self) -> Self:
        check_public_link(self.url)
        return self


class PersonalizationDeclaration(EmailModel):
    name: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")]
    source_policy: OpaqueRef
    required: bool = True
    missing_value_behavior: Literal["refuse"] = "refuse"


class EmailCompliance(ScopedEmailModel):
    footer_policy: EmailArtifactRef
    unsubscribe_policy: EmailArtifactRef
    consent_policy: EmailArtifactRef | None
    suppression_policy: EmailArtifactRef | None
    footer_text: Text
    unsubscribe_link_id: OpaqueRef


class EmailCampaignPlan(EmailArtifact):
    publication_profile: EmailArtifactRef
    business_objective: Text
    audience: AudienceIntent
    campaign_window: ResearchWindow
    calls_to_action: tuple[EmailCTA, ...] = Field(min_length=1)
    conversion_objectives: tuple[EmailArtifactRef, ...] = Field(min_length=1)
    attribution_policy: EmailArtifactRef
    tracking_policy: EmailArtifactRef
    required_human_approvals: tuple[OpaqueRef, ...] = Field(min_length=1)
    assumptions: tuple[Text, ...] = ()
    risks: tuple[Text, ...] = ()
    stopping_conditions: tuple[Text, ...] = Field(min_length=1)
    generation: GenerationTrace

    @model_validator(mode="after")
    def campaign_ctas_are_exact(self) -> Self:
        exact_ctas(self.calls_to_action)
        return self


class EmailSequenceStepPlan(ScopedEmailModel):
    step_id: OpaqueRef
    ordinal: int = Field(ge=1, le=100)
    message_plan: EmailArtifactRef
    delay_seconds: int = Field(ge=0, le=31536000)
    delay_anchor: Literal["preceding_admitted_event"] = "preceding_admitted_event"
    purpose: Text
    desired_audience_action: Text
    send_window_policy: EmailArtifactRef
    skip_policy: EmailArtifactRef
    exit_policy: EmailArtifactRef
    freshness_max_age_seconds: int = Field(ge=1)
    required_approval_class: OpaqueRef


class EmailSequencePlan(EmailArtifact):
    campaign_or_lifecycle_program: EmailArtifactRef
    entry_policy: EmailArtifactRef
    exit_policy: EmailArtifactRef
    conversion_policy: EmailArtifactRef
    suppression_policy: EmailArtifactRef
    steps: tuple[EmailSequenceStepPlan, ...] = Field(min_length=1, max_length=100)
    send_window_policy: EmailArtifactRef
    quiet_hours_policy: EmailArtifactRef
    time_zone_policy: EmailArtifactRef
    maximum_enrolment_window: ResearchWindow
    required_provider_semantics: tuple[OpaqueRef, ...] = Field(min_length=1)
    existing_enrollee_migration_policy: Literal[
        "retain_existing_revision", "explicit_new_authority"
    ]
    migration_policy: EmailArtifactRef | None = None
    activation_requirements: tuple[OpaqueRef, ...] = Field(min_length=1)
    approval_requirements: tuple[OpaqueRef, ...] = Field(min_length=1)
    previous_revision: EmailArtifactRef | None = None
    generation: GenerationTrace

    @model_validator(mode="after")
    def linear_immutable_revision(self) -> Self:
        if tuple(step.ordinal for step in self.steps) != tuple(range(1, len(self.steps) + 1)):
            raise ValueError("sequence ordinals must be contiguous and ordered from one")
        if len({step.step_id for step in self.steps}) != len(self.steps):
            raise ValueError("sequence step identities must be unique")
        if self.previous_revision:
            if (
                self.previous_revision.ref != self.artifact_id
                or self.revision != self.previous_revision.revision + 1
            ):
                raise ValueError("sequence edits require the next immutable revision")
        elif self.revision != 1:
            raise ValueError("later sequence revisions require a predecessor binding")
        if (
            self.existing_enrollee_migration_policy == "explicit_new_authority"
            and not self.migration_policy
        ):
            raise ValueError(
                "enrollee migration requires an explicit policy and separate runtime authority"
            )
        return self


class EmailMessagePlan(EmailArtifact):
    publication_profile: EmailArtifactRef
    campaign: EmailArtifactRef
    purpose: Text
    objective: Text
    audience: AudienceIntent
    lifecycle_stage: OpaqueRef
    subject_direction: Text
    preheader_direction: Text
    required_sections: tuple[Text, ...] = Field(min_length=1)
    calls_to_action: tuple[EmailCTA, ...] = Field(min_length=1)
    personalization: tuple[PersonalizationDeclaration, ...] = ()
    links: tuple[EmailLink, ...] = Field(min_length=1)
    tracking_policy: EmailArtifactRef
    sender_identity: EmailArtifactRef
    reply_to_identity: EmailArtifactRef
    compliance: EmailCompliance
    source_evidence: tuple[EmailArtifactRef, ...] = Field(min_length=1)
    brand_policy: EmailArtifactRef
    voice_policy: EmailArtifactRef
    accessibility_requirements: tuple[Text, ...] = Field(min_length=1)
    preview_required: bool = True
    test_send_required: bool = True
    newsletter_issue: EmailArtifactRef | None = None
    generation: GenerationTrace

    @model_validator(mode="after")
    def cta_plan_is_exact(self) -> Self:
        exact_ctas(self.calls_to_action)
        links = {row.link_id: row for row in self.links}
        if len(links) != len(self.links):
            raise ValueError("message link identities must be unique")
        if any(
            row.link_id not in links or links[row.link_id].purpose != "cta"
            for row in self.calls_to_action
        ):
            raise ValueError("CTA links must have CTA purpose")
        return self


class EmailMessageDraft(EmailArtifact):
    message_plan: EmailArtifactRef
    subject: Annotated[str, Field(min_length=1, max_length=998, pattern=r"^[^\r\n]+$")]
    preheader: Annotated[str, Field(min_length=1, max_length=998, pattern=r"^[^\r\n]+$")]
    html: Annotated[str, Field(min_length=1, max_length=1000000)]
    plain_text: Annotated[str, Field(min_length=1, max_length=1000000)]
    links: tuple[EmailLink, ...] = Field(min_length=1)
    calls_to_action: tuple[EmailCTA, ...] = Field(min_length=1)
    personalization: tuple[PersonalizationDeclaration, ...] = ()
    sender_identity: EmailArtifactRef
    reply_to_identity: EmailArtifactRef
    compliance: EmailCompliance
    source_lineage: tuple[EmailArtifactRef, ...] = Field(min_length=1)
    generation: GenerationTrace

    @model_validator(mode="after")
    def manifest_identity(self) -> Self:
        for values in (
            tuple(link.link_id for link in self.links),
            tuple(cta.cta_id for cta in self.calls_to_action),
            tuple(token.name for token in self.personalization),
        ):
            if len(set(values)) != len(values):
                raise ValueError("manifest identities must be unique")
        links = {link.link_id: link for link in self.links}
        if any(
            cta.link_id not in links or links[cta.link_id].purpose != "cta"
            for cta in self.calls_to_action
        ):
            raise ValueError("CTA must resolve to the link manifest")
        unsubscribe = links.get(self.compliance.unsubscribe_link_id)
        if not unsubscribe or unsubscribe.purpose != "unsubscribe":
            raise ValueError("compliance must identify an unsubscribe link")
        if sum(cta.primary for cta in self.calls_to_action) != 1:
            raise ValueError("draft requires exactly one primary CTA")
        return self


EmailReviewCheck = Literal[
    "source_traceability",
    "publication_voice",
    "audience_policy",
    "subject_body",
    "html_plain_text",
    "links",
    "cta",
    "personalization",
    "accessibility",
    "footer_unsubscribe",
    "consent_suppression",
    "claims",
]
REVIEW_CHECKS: tuple[EmailReviewCheck, ...] = (
    "source_traceability",
    "publication_voice",
    "audience_policy",
    "subject_body",
    "html_plain_text",
    "links",
    "cta",
    "personalization",
    "accessibility",
    "footer_unsubscribe",
    "consent_suppression",
    "claims",
)


class EmailReviewFinding(EmailModel):
    check: EmailReviewCheck
    status: Literal["pass", "blocked", "human_needed"]
    reason: OpaqueRef


class EmailExecutionContext(ScopedEmailModel):
    provider_kind: OpaqueRef
    connection_ref: OpaqueRef
    account_ref: OpaqueRef
    connector_revision: OpaqueRef
    lowering_profile: EmailArtifactRef


class EmailLoweringEvidence(EmailArtifact):
    receipt: EmailArtifactRef
    issuer: EmailArtifactRef
    receipt_contract: CapabilityId
    receipt_contract_digest: Digest
    execution: EmailExecutionContext
    draft: EmailArtifactRef
    sender_identity: EmailArtifactRef
    template_mapping_digest: Digest
    submitted_payload_digest: Digest
    observed_payload_digest: Digest
    rendered_preview_digest: Digest
    covered_snapshot_digest: Digest
    covered_tokens: tuple[OpaqueRef, ...] = ()
    missing_value_behavior: Literal["refuse"] = "refuse"
    outcome: Literal["verified", "needs_review", "ambiguous"]

    @model_validator(mode="after")
    def exact_lowering(self) -> Self:
        if len(set(self.covered_tokens)) != len(self.covered_tokens):
            raise ValueError("token coverage must be unique")
        if (
            self.outcome == "verified"
            and self.submitted_payload_digest != self.observed_payload_digest
        ):
            raise ValueError("material transformation requires review")
        return self


class EmailReviewEvidence(EmailArtifact):
    """Caller-supplied review evidence; authenticity is verified by the controlling runtime."""

    draft: EmailArtifactRef
    check: EmailReviewCheck
    passed: bool
    policy: EmailArtifactRef
    receipt: EmailArtifactRef
    issuer: EmailArtifactRef
    lowering: EmailLoweringEvidence | None = None
    valid_until: UtcDatetime


class EmailEditorialReview(EmailArtifact):
    plan: EmailArtifactRef
    draft: EmailArtifactRef
    findings: tuple[EmailReviewFinding, ...]
    evidence: tuple[EmailReviewEvidence, ...] = ()
    ready_for_human_approval: bool
    generation: GenerationTrace

    @model_validator(mode="after")
    def no_self_approval(self) -> Self:
        if sorted(row.check for row in self.findings) != sorted(REVIEW_CHECKS):
            raise ValueError("review requires exactly one finding for every check")
        if self.ready_for_human_approval != all(row.status == "pass" for row in self.findings):
            raise ValueError("review readiness must match every finding")
        return self


class EmailProofReceipt(EmailArtifact):
    draft: EmailArtifactRef
    kind: Literal["preview", "test_send"]
    lowering: EmailLoweringEvidence
    audience_snapshot: AudienceSnapshotSummary | None = None
    personalization_resolved: bool
    successful: bool
    valid_until: UtcDatetime

    @model_validator(mode="after")
    def test_is_separate(self) -> Self:
        if self.kind == "test_send" and (
            self.audience_snapshot is None or self.audience_snapshot.purpose != "test"
        ):
            raise ValueError("test evidence requires a separate test audience")
        return self


class EmailDeliveryMaterial(ScopedEmailModel):
    campaign_release: EmailArtifactRef
    execution: EmailExecutionContext
    template_mapping_digest: Digest
    draft: EmailMessageDraft
    html_digest: Digest
    plain_text_digest: Digest
    link_manifest_digest: Digest
    audience_snapshot: AudienceSnapshotSummary
    tracking_policy: EmailArtifactRef
    schedule_intent: UtcDatetime | None = None
    campaign: EmailArtifactRef
    sequence_revision: EmailArtifactRef | None = None
    review: EmailEditorialReview
    proofs: tuple[EmailProofReceipt, ...] = ()

    @model_validator(mode="after")
    def exact_material(self) -> Self:
        if (
            self.html_digest != canonical_digest(self.draft.html)
            or self.plain_text_digest != canonical_digest(self.draft.plain_text)
            or self.link_manifest_digest != canonical_digest(self.draft.links)
            or self.review.draft != self.draft.binding()
        ):
            raise ValueError("delivery material does not match the exact draft")
        return self


class EmailDeliveryPackage(EmailArtifact):
    material: EmailDeliveryMaterial
    approval_digest: Digest

    @model_validator(mode="after")
    def exact_approval(self) -> Self:
        if self.approval_digest != canonical_digest(self.material):
            raise ValueError("approval digest does not match delivery material")
        return self


class EmailEffectIntent(StrEnum):
    """Editorial intent only. Zeocore owns the executable operation vocabulary."""

    CREATE_DRAFT = "create_remote_draft"
    UPDATE_DRAFT = "update_remote_draft"
    TEST = "send_test"
    SCHEDULE = "schedule_broadcast"
    SEND = "send_broadcast"
    PROVISION = "provision_sequence_revision"
    ACTIVATE = "activate_sequence_revision"
    ENROL = "enrol_audience_snapshot"
    PAUSE = "pause_future_steps"
    CANCEL = "cancel_scheduled_broadcast"
    RETIRE = "retire_sequence_revision"
    MIGRATE = "migrate_existing_enrollees"


class EmailContentResult(ScopedEmailModel):
    delivery: EmailArtifactRef
    message_plan: EmailArtifactRef
    audience: AudienceSnapshotSummary


class EmailDraftResult(EmailContentResult):
    kind: Literal["draft"] = "draft"
    intent: Literal[EmailEffectIntent.CREATE_DRAFT, EmailEffectIntent.UPDATE_DRAFT]


class EmailScheduledResult(EmailContentResult):
    kind: Literal["scheduled_broadcast"] = "scheduled_broadcast"
    intent: Literal[EmailEffectIntent.SCHEDULE] = EmailEffectIntent.SCHEDULE


class EmailBroadcastResult(EmailContentResult):
    kind: Literal["broadcast"] = "broadcast"
    intent: Literal[EmailEffectIntent.SEND] = EmailEffectIntent.SEND


class EmailTestResult(EmailContentResult):
    kind: Literal["test_send"] = "test_send"
    intent: Literal[EmailEffectIntent.TEST] = EmailEffectIntent.TEST


class EmailCancelledResult(EmailContentResult):
    kind: Literal["cancelled_broadcast"] = "cancelled_broadcast"
    intent: Literal[EmailEffectIntent.CANCEL] = EmailEffectIntent.CANCEL


class EmailSequenceResult(ScopedEmailModel):
    kind: Literal["sequence_revision"] = "sequence_revision"
    intent: Literal[
        EmailEffectIntent.PROVISION,
        EmailEffectIntent.ACTIVATE,
        EmailEffectIntent.ENROL,
        EmailEffectIntent.PAUSE,
        EmailEffectIntent.RETIRE,
        EmailEffectIntent.MIGRATE,
    ]
    sequence: EmailArtifactRef
    lifecycle_state: Literal["provisioned", "active", "paused", "retired"]
    audience: AudienceSnapshotSummary | None = None

    @model_validator(mode="after")
    def exact_sequence_result(self) -> Self:
        states = {
            EmailEffectIntent.PROVISION: "provisioned",
            EmailEffectIntent.ACTIVATE: "active",
            EmailEffectIntent.ENROL: "active",
            EmailEffectIntent.PAUSE: "paused",
            EmailEffectIntent.RETIRE: "retired",
            EmailEffectIntent.MIGRATE: "provisioned",
        }
        if self.lifecycle_state != states[self.intent]:
            raise ValueError("sequence result state contradicts its effect")
        needs_audience = self.intent in {EmailEffectIntent.ENROL, EmailEffectIntent.MIGRATE}
        if needs_audience != (self.audience is not None):
            raise ValueError("sequence result audience contradicts its effect")
        if self.audience is not None and self.audience.purpose != "production":
            raise ValueError("sequence result requires a production audience")
        return self


EmailRemoteResult = Annotated[
    EmailDraftResult
    | EmailScheduledResult
    | EmailBroadcastResult
    | EmailTestResult
    | EmailCancelledResult
    | EmailSequenceResult,
    Field(discriminator="kind"),
]


class EmailRemoteReceipt(EmailArtifact):
    result: EmailRemoteResult
    operation: EmailArtifactRef
    campaign_release: EmailArtifactRef
    execution: EmailExecutionContext
    issuer: EmailArtifactRef
    receipt_contract: CapabilityId
    receipt_contract_digest: Digest
    remote_ref: OpaqueRef
    remote_revision_digest: Digest
    outcome: Literal["confirmed", "needs_review", "ambiguous"]

    @model_validator(mode="after")
    def exact_result_context(self) -> Self:
        audience = self.result.audience
        if audience is not None and (
            audience.provider_kind != self.execution.provider_kind
            or audience.connection_ref != self.execution.connection_ref
        ):
            raise ValueError("receipt audience execution mismatch")
        if isinstance(self.result, EmailContentResult):
            expected = "test" if self.result.intent == EmailEffectIntent.TEST else "production"
            if (
                self.result.intent
                not in {EmailEffectIntent.CREATE_DRAFT, EmailEffectIntent.UPDATE_DRAFT}
                and self.result.audience.purpose != expected
            ):
                raise ValueError("receipt effect and audience purpose mismatch")
        return self

    @property
    def kind(self) -> str:
        return self.result.kind

    @property
    def delivery(self) -> EmailArtifactRef | None:
        return self.result.delivery if isinstance(self.result, EmailContentResult) else None

    @property
    def message_plan(self) -> EmailArtifactRef | None:
        return self.result.message_plan if isinstance(self.result, EmailContentResult) else None

    @property
    def sequence(self) -> EmailArtifactRef | None:
        return self.result.sequence if isinstance(self.result, EmailSequenceResult) else None

    @property
    def lifecycle_state(self) -> str | None:
        return self.result.lifecycle_state if isinstance(self.result, EmailSequenceResult) else None


class EmailMigrationStep(EmailModel):
    source_step: OpaqueRef
    target_step: OpaqueRef | None
    disposition: Literal["retain", "skip", "restart"]


class EmailMigrationPlan(ScopedEmailModel):
    target_receipt: EmailRemoteReceipt
    source_sequence: EmailArtifactRef
    target_sequence: EmailArtifactRef
    enrollees: AudienceSnapshotSummary
    policy: EmailArtifactRef
    steps: tuple[EmailMigrationStep, ...] = Field(min_length=1)


class EmailOperationIntent(ScopedEmailModel):
    execution: EmailExecutionContext
    campaign_release: EmailArtifactRef
    originating_operation: EmailArtifactRef | None = None
    target_delivery: EmailArtifactRef | None = None
    prior_receipt: EmailRemoteReceipt | None = None
    migration: EmailMigrationPlan | None = None
    intent: EmailEffectIntent
    operation: CapabilityId
    operation_contract_digest: Digest
    delivery: EmailArtifactRef | None = None
    delivery_approval_digest: Digest | None = None
    sequence: EmailArtifactRef | None = None
    audience: AudienceSnapshotSummary | None = None
    target_remote_ref: OpaqueRef | None = None
    expected_remote_revision_digest: Digest | None = None
    migration_policy: EmailArtifactRef | None = None

    @model_validator(mode="after")
    def distinct_effect_requirements(self) -> Self:
        content_effects = {
            EmailEffectIntent.CREATE_DRAFT,
            EmailEffectIntent.UPDATE_DRAFT,
            EmailEffectIntent.TEST,
            EmailEffectIntent.SCHEDULE,
            EmailEffectIntent.SEND,
        }
        sequence_effects = {
            EmailEffectIntent.PROVISION,
            EmailEffectIntent.ACTIVATE,
            EmailEffectIntent.ENROL,
            EmailEffectIntent.PAUSE,
            EmailEffectIntent.RETIRE,
            EmailEffectIntent.MIGRATE,
        }
        if self.intent in content_effects and (
            not self.delivery or not self.delivery_approval_digest
        ):
            raise ValueError("content effects require an exact delivery binding")
        if self.intent in sequence_effects and not self.sequence:
            raise ValueError("sequence effects require an exact sequence revision")
        if self.intent in {
            EmailEffectIntent.TEST,
            EmailEffectIntent.SEND,
            EmailEffectIntent.SCHEDULE,
            EmailEffectIntent.ENROL,
            EmailEffectIntent.MIGRATE,
        }:
            if not self.audience:
                raise ValueError("effect requires an exact audience snapshot")
            expected = "test" if self.intent == EmailEffectIntent.TEST else "production"
            if self.audience.purpose != expected:
                raise ValueError("test and production audiences are distinct")
        if (
            self.intent in {EmailEffectIntent.ACTIVATE, EmailEffectIntent.PROVISION}
            and self.audience
        ):
            raise ValueError("activation cannot authorize audience enrolment")
        if self.intent in {
            EmailEffectIntent.ACTIVATE,
            EmailEffectIntent.ENROL,
            EmailEffectIntent.MIGRATE,
            EmailEffectIntent.UPDATE_DRAFT,
            EmailEffectIntent.CANCEL,
            EmailEffectIntent.PAUSE,
            EmailEffectIntent.RETIRE,
        }:
            if (
                not self.target_remote_ref
                or not self.expected_remote_revision_digest
                or not self.prior_receipt
            ):
                raise ValueError("remote mutation requires a target and immutable prior receipt")
        if self.intent == EmailEffectIntent.PROVISION and (
            self.prior_receipt or self.delivery or self.target_remote_ref
        ):
            raise ValueError(
                "provisioning creates a sequence revision without activation or a prior target"
            )
        if self.intent in {EmailEffectIntent.CANCEL, EmailEffectIntent.UPDATE_DRAFT}:
            if not self.originating_operation or not self.target_delivery or not self.prior_receipt:
                raise ValueError(
                    "delivery mutation requires its originating operation and target delivery"
                )
            if (
                self.prior_receipt.operation != self.originating_operation
                or self.prior_receipt.delivery != self.target_delivery
            ):
                raise ValueError(
                    "delivery mutation receipt does not bind its originating operation and delivery"
                )
            if (
                self.intent == EmailEffectIntent.CANCEL
                and self.delivery is not None
                and self.delivery != self.target_delivery
            ):
                raise ValueError("cancellation delivery differs from its target")
        elif self.originating_operation or self.target_delivery:
            raise ValueError("originating delivery fields belong only to delivery mutations")
        if self.prior_receipt:
            receipt = self.prior_receipt
            if (
                receipt.execution != self.execution
                or receipt.remote_ref != self.target_remote_ref
                or receipt.remote_revision_digest != self.expected_remote_revision_digest
                or receipt.outcome != "confirmed"
            ):
                raise ValueError("remote target and receipt provenance mismatch")
            if (
                self.intent != EmailEffectIntent.MIGRATE
                and receipt.campaign_release != self.campaign_release
            ):
                raise ValueError("remote receipt belongs to another campaign release")
            if self.intent == EmailEffectIntent.UPDATE_DRAFT and receipt.kind != "draft":
                raise ValueError("draft update requires an original draft receipt")
            if self.intent == EmailEffectIntent.CANCEL and receipt.kind != "scheduled_broadcast":
                raise ValueError("cancellation requires the original scheduling receipt")
            if self.intent in {
                EmailEffectIntent.ACTIVATE,
                EmailEffectIntent.ENROL,
                EmailEffectIntent.PAUSE,
                EmailEffectIntent.RETIRE,
            } and (receipt.kind != "sequence_revision" or receipt.sequence != self.sequence):
                raise ValueError("sequence mutation requires exact remote revision evidence")
        required_states = {
            EmailEffectIntent.ACTIVATE: {"provisioned"},
            EmailEffectIntent.ENROL: {"active"},
            EmailEffectIntent.PAUSE: {"active"},
            EmailEffectIntent.RETIRE: {"active", "paused"},
            EmailEffectIntent.MIGRATE: {"paused"},
        }
        if self.intent in required_states and (
            self.prior_receipt is None
            or self.prior_receipt.lifecycle_state not in required_states[self.intent]
        ):
            raise ValueError("sequence transition requires the declared prior lifecycle state")
        if self.intent == EmailEffectIntent.MIGRATE:
            if (
                not self.migration
                or self.migration.policy != self.migration_policy
                or self.migration.target_sequence != self.sequence
                or self.migration.enrollees != self.audience
            ):
                raise ValueError(
                    "migration requires exact source target population and step policy"
                )
            if (
                self.prior_receipt is None
                or self.prior_receipt.kind != "sequence_revision"
                or self.prior_receipt.sequence != self.migration.source_sequence
            ):
                raise ValueError("migration source requires an exact sequence receipt")
            target = self.migration.target_receipt
            if (
                target.kind != "sequence_revision"
                or target.lifecycle_state != "provisioned"
                or target.sequence != self.sequence
                or target.execution != self.execution
                or target.campaign_release != self.campaign_release
                or target.outcome != "confirmed"
            ):
                raise ValueError("migration target requires an exact provisioned sequence receipt")
        elif self.migration or self.migration_policy:
            raise ValueError("migration cannot be authorized through another effect")
        return self


class ProposedEmailOperation(EmailArtifact):
    material: EmailOperationIntent
    approval_digest: Digest
    idempotency_key: OpaqueRef

    @model_validator(mode="after")
    def exact_effect_approval(self) -> Self:
        if self.approval_digest != effect_approval_digest(self.material, self.idempotency_key):
            raise ValueError("effect approval digest does not match logical operation identity")
        return self


def effect_approval_digest(material: EmailOperationIntent, key: str) -> str:
    return canonical_digest({"material": material, "idempotency_key": key})


class EmailCampaignRelease(EmailArtifact):
    campaign: EmailCampaignPlan
    messages: tuple[EmailMessagePlan, ...] = Field(min_length=1)
    sequences: tuple[EmailSequencePlan, ...] = ()
    calls_to_action: tuple[EmailCTA, ...] = Field(min_length=1)
    measurement_plan: tuple[EmailArtifactRef, ...] = Field(min_length=1)
    generation: GenerationTrace

    @model_validator(mode="after")
    def acyclic_membership(self) -> Self:
        if len({row.artifact_id for row in self.messages}) != len(self.messages) or len(
            {row.artifact_id for row in self.sequences}
        ) != len(self.sequences):
            raise ValueError("release members must have unique identities")
        if any(row.audience != self.campaign.audience for row in self.messages):
            raise ValueError("release messages must use the campaign audience")
        if any(row.campaign != self.campaign.binding() for row in self.messages) or any(
            row.campaign_or_lifecycle_program != self.campaign.binding() for row in self.sequences
        ):
            raise ValueError("release members must bind the exact campaign plan")
        members = tuple(row.binding() for row in self.messages)
        if any(step.message_plan not in members for row in self.sequences for step in row.steps):
            raise ValueError("sequence steps must belong to release messages")
        declared = exact_ctas(self.campaign.calls_to_action)
        used: dict[str, EmailCTA] = {}
        for message in self.messages:
            for identity, cta in exact_ctas(message.calls_to_action).items():
                if identity not in declared or declared[identity] != cta:
                    raise ValueError("release CTA identity has conflicting definitions")
                used[identity] = cta
        expected = tuple(used.values())
        if used != declared:
            raise ValueError(
                "every campaign CTA must be used and every message CTA must be declared"
            )
        if (
            self.calls_to_action != expected
            or self.measurement_plan != self.campaign.conversion_objectives
        ):
            raise ValueError("release CTA and measurement plan must match members")
        return self


EmailMetricName = Literal[
    "attempted",
    "accepted",
    "delivered",
    "deferred",
    "bounced",
    "complained",
    "unsubscribed",
    "opened",
    "unique_link_clicks",
    "cta_conversions",
    "sequence_enrolments",
    "step_completion",
    "step_exit",
    "campaign_conversion",
    "attributed_revenue",
]


def admissible_metrics(receipt: EmailRemoteReceipt) -> frozenset[str]:
    result = receipt.result
    if (
        receipt.outcome != "confirmed"
        or result.audience is None
        or result.audience.purpose != "production"
    ):
        return frozenset()
    if isinstance(result, EmailBroadcastResult):
        return frozenset(
            {
                "attempted",
                "accepted",
                "delivered",
                "deferred",
                "bounced",
                "complained",
                "unsubscribed",
                "opened",
                "unique_link_clicks",
                "cta_conversions",
                "campaign_conversion",
                "attributed_revenue",
            }
        )
    if isinstance(result, EmailSequenceResult) and result.intent == EmailEffectIntent.ENROL:
        return frozenset({"sequence_enrolments", "step_completion", "step_exit"})
    return frozenset()


class EmailMetricObservation(EmailArtifact):
    campaign_release: EmailArtifactRef
    operation_receipt: EmailRemoteReceipt
    campaign: EmailArtifactRef
    operation: EmailArtifactRef
    retrieval_receipt: EmailArtifactRef
    provider_kind: OpaqueRef
    connection_ref: OpaqueRef
    aggregate_segment_ref: OpaqueRef
    observation_window: ResearchWindow
    metric: EmailMetricName
    value: float = Field(ge=0, allow_inf_nan=False)
    unit: Literal["count", "rate", "currency"]
    numerator: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    denominator: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    provider_definition: Text
    provider_definition_version: OpaqueRef
    completeness: Literal["complete", "partial", "unknown"]
    coverage: float = Field(ge=0, le=1, allow_inf_nan=False)
    reliability: Literal["qualified", "unreliable", "unknown"]
    reliability_notes: tuple[Text, ...] = ()
    attribution_policy: EmailArtifactRef | None = None
    attribution_assumptions: tuple[Text, ...] = ()
    data_gaps: tuple[Text, ...] = ()

    @model_validator(mode="after")
    def qualified_metrics(self) -> Self:
        receipt = self.operation_receipt
        if self.metric not in admissible_metrics(receipt):
            raise ValueError("metric is not admissible for this production effect receipt")
        if (
            receipt.operation != self.operation
            or receipt.campaign_release != self.campaign_release
            or receipt.execution.provider_kind != self.provider_kind
            or receipt.execution.connection_ref != self.connection_ref
            or receipt.outcome != "confirmed"
        ):
            raise ValueError("metric operation receipt provenance mismatch")
        if self.numerator is not None and self.unit != "rate":
            raise ValueError("numerator and denominator require rate unit")
        if (self.numerator is None) != (self.denominator is None):
            raise ValueError("ratios require a numerator and nonzero denominator")
        if self.unit == "rate" and (
            self.numerator is None
            or self.denominator is None
            or abs(self.value - self.numerator / self.denominator) > 1e-12
        ):
            raise ValueError("rate must equal its declared numerator over denominator")
        if self.metric == "attributed_revenue" and not self.attribution_policy:
            raise ValueError("revenue requires an explicit attribution policy")
        if self.metric == "opened" and not self.reliability_notes:
            raise ValueError("opens require reliability qualifications")
        if self.completeness == "complete" and (self.coverage != 1 or self.data_gaps):
            raise ValueError("complete observations must have full coverage and no gaps")
        return self


class EmailStoppingConditionFinding(EmailModel):
    condition: Text
    status: Literal["human_needed"] = "human_needed"


class EmailMeasurementPopulation(ScopedEmailModel):
    release: EmailCampaignRelease
    operations: tuple[EmailRemoteReceipt, ...]
    aggregation_policy: Literal["per_operation_no_pooling"] = "per_operation_no_pooling"

    @model_validator(mode="after")
    def exact_population(self) -> Self:
        if len({row.operation for row in self.operations}) != len(self.operations):
            raise ValueError("expected operations must be unique")
        members = {row.binding() for row in self.release.messages}
        sequences = {row.binding() for row in self.release.sequences}
        for receipt in self.operations:
            if not admissible_metrics(receipt):
                raise ValueError(
                    "measurement population requires an eligible production effect receipt"
                )
            if receipt.campaign_release != self.release.binding() or receipt.outcome != "confirmed":
                raise ValueError("expected receipt must confirm the exact campaign release")
            if receipt.message_plan is not None and receipt.message_plan not in members:
                raise ValueError("expected operation refers to another message")
            if receipt.sequence is not None and receipt.sequence not in sequences:
                raise ValueError("expected operation refers to another sequence")
            if receipt.message_plan is None and receipt.sequence is None:
                raise ValueError("expected operation requires a message or sequence binding")
        return self

    def gaps(
        self, observations: tuple[EmailMetricObservation, ...], metrics: tuple[EmailMetricName, ...]
    ) -> tuple[str, ...]:
        covered = {row.message_plan for row in self.operations}
        missing_messages = tuple(
            f"Unmeasured release message: {row.artifact_id}"
            for row in self.release.messages
            if row.binding() not in covered
        )
        present = {(row.operation, row.metric) for row in observations}
        missing_cells = tuple(
            f"Missing operation metric: {receipt.operation.ref}/{metric}"
            for receipt in self.operations
            for metric in metrics
            if metric in admissible_metrics(receipt) and (receipt.operation, metric) not in present
        )
        return (*missing_messages, *missing_cells)


class EmailProgramAssessment(EmailArtifact):
    population: EmailMeasurementPopulation
    campaign_release: EmailArtifactRef
    expected_metrics: tuple[EmailMetricName, ...] = Field(min_length=1)
    stopping_conditions: tuple[EmailStoppingConditionFinding, ...]
    campaign: EmailArtifactRef
    observation_window: ResearchWindow
    observations: tuple[EmailMetricObservation, ...]
    completeness: Literal["complete", "partial", "unknown"]
    confidence: Literal["limited", "qualified"]
    conclusions: tuple[Text, ...]
    data_gaps: tuple[Text, ...]
    hypotheses: tuple[Text, ...]
    generation: GenerationTrace

    @model_validator(mode="after")
    def no_overstatement(self) -> Self:
        if len(set(self.expected_metrics)) != len(self.expected_metrics):
            raise ValueError("expected metrics must be unique")
        if any(
            row.observation_window != self.observation_window
            or row.campaign_release != self.campaign_release
            for row in self.observations
        ):
            raise ValueError("assessment window or release mismatch")
        cohorts = {
            (canonical_digest(row.operation_receipt.execution), row.aggregate_segment_ref)
            for row in self.observations
        }
        if len(cohorts) > 1:
            raise ValueError("assessment requires one provider connection and aggregate cohort")
        if (
            self.population.release.binding() != self.campaign_release
            or self.population.release.campaign.binding() != self.campaign
        ):
            raise ValueError("assessment population release mismatch")
        if any(
            row.operation_receipt not in self.population.operations for row in self.observations
        ):
            raise ValueError("observation not in the declared operation population")
        population_gaps = self.population.gaps(self.observations, self.expected_metrics)
        conflicts = metric_conflicts(self.observations)
        complete = (
            bool(self.observations)
            and not conflicts
            and not population_gaps
            and not self.data_gaps
            and set(self.expected_metrics) <= {row.metric for row in self.observations}
            and all(
                item.completeness == "complete" and item.reliability == "qualified"
                for item in self.observations
            )
        )
        if not complete and (self.completeness == "complete" or self.confidence != "limited"):
            raise ValueError(
                "partial or unreliable observations cannot support a complete assessment"
            )
        if any(item.campaign != self.campaign for item in self.observations):
            raise ValueError("assessment observations must bind the same campaign revision")
        return self


def metric_conflicts(rows: tuple[EmailMetricObservation, ...]) -> bool:
    groups: dict[tuple[str, str, str], set[str]] = {}
    for row in rows:
        key = (row.metric, row.operation.digest, row.aggregate_segment_ref)
        groups.setdefault(key, set()).add(
            canonical_digest(
                (
                    row.value,
                    row.unit,
                    row.numerator,
                    row.denominator,
                    row.provider_definition,
                    row.provider_definition_version,
                )
            )
        )
    return any(len(values) > 1 for values in groups.values())
