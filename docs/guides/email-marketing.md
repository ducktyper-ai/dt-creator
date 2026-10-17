# Email marketing

<!-- Reviewed 2026-09-08. Email v4 discriminates receipt results, lifecycle states and admissible metrics; v1/v2/v3 preparation APIs are retired; original schemas remain archived. -->

Creator designs and evaluates email programs. Zeocore owns the public provider
contracts and lowering; ZEOconnect executes provider effects; Runtime owns
approvals, audience authorization, schedules and retries; Newsroom owns durable
publication history and observations. Any third-party host can implement these
responsibilities without importing private ZEO packages.

## Concepts and contracts

| Concept | Public artifact | Meaning |
|---|---|---|
| Campaign | `EmailCampaignPlan` | Bounded objective, audience, CTAs, attribution and stopping conditions |
| Campaign release | `EmailCampaignRelease` | Exact campaign, message and sequence membership, CTAs and measurement plan without cyclic digests |
| Sequence | `EmailSequencePlan` | Ordered immutable revision with explicit policy references and delays |
| Step | `EmailSequenceStepPlan` | Stable identity/ordinal, exact message-plan digest, admitted-event delay and freshness |
| Message | `EmailMessagePlan`, `EmailMessageDraft` | Editorial intent and exact subject, preheader, HTML, plain text and manifests |
| Audience intent | `AudienceIntent` | Segments, inclusions/exclusions, consent, suppression, geography, frequency and cross-publication policy |
| Audience snapshot | `AudienceSnapshotSummary` | Opaque runtime-supplied selection with digest, counts, provider/connection, expiry and drift state |
| Review | `EmailEditorialReview` | Structural checks plus supplied evidence, ready only for human approval |
| Delivery | `EmailDeliveryPackage` | Exact creative material and approval target digest |
| Effect intent | `ProposedEmailOperation` | Separate proposal referring to a public Zeocore `CapabilityId` and contract digest |
| Learning | `EmailMetricObservation`, `EmailProgramAssessment` | Receipt-linked aggregate input and qualified conclusions |

A newsletter is a periodic editorial issue sent as a one-off broadcast. A campaign
need not correspond to a provider-side campaign object. A lifecycle program is
the broader journey containing entry/exit/conversion/suppression policies; v4 can
represent it through one linear sequence. HubSpot Sales Sequences are outside
this model; the integration target is HubSpot Marketing.

## Invoke the nine capabilities

Use the standard capability registry and typed requests from
`zeo_creator.capabilities.email_marketing`. All nine capabilities declare only
Zeocore's conservative `read` effect, carry a `pure` tag, and have no required
acquisition services or network access:

```text
creator.plan_email_campaign@4.0.0
creator.finalize_email_campaign@4.0.0
creator.propose_email_operation@4.0.0
creator.plan_email_sequence@4.0.0
creator.plan_email_message@4.0.0
creator.compose_email_message@4.0.0
creator.review_email_message@4.0.0
creator.prepare_email_delivery@4.0.0
creator.assess_email_program@4.0.0
```

Composition accepts an optional `creator.email_strategy` implementing
`EmailCreativeStrategy.compose(plan, sections, created_at)`. The strategy receives
only supplied editorial inputs; it is not passed `ToolContext`, credentials or a
connector. Its returned scope, input digests and artifact integrity are checked.
The deterministic strategy copies curated source sections into matching HTML and
plain text and adds the declared CTAs and compliance footer.

## Review and readiness

Review covers source lineage, voice, audience policy, subject/body consistency,
HTML/plain-text consistency, links, CTAs, personalization, accessibility,
footer/unsubscribe, consent/suppression and claims. Preview and test evidence belong exclusively to delivery preparation. An editorial review can be ready before either external check exists; it does not claim they passed. Optional preview/test requirements do not block editorial review.

The deterministic reviewer compares visible HTML text with plain text and rejects
unlisted markup/attributes. This intentionally conservative subset supports text
and descriptive links; richer email templates need explicit future contract work
and qualified render validation. Syntactically valid links do not prove remote
availability. Voice, subject/body consistency, accessibility, link validation and claim review
require supplied `EmailReviewEvidence` bound to the exact draft and an expiry.
The parser checks anchor labels against their declared CTA targets and the unsubscribe target. Exactly one CTA must be primary; sequence intent selects that CTA regardless of position. Missing evidence produces `human_needed`; it cannot be upgraded by a boolean
readiness claim. Delivery preparation repeats the checks at preparation time.

Tokens remain symbolic declarations with missing-value behavior `refuse`.
Undeclared or malformed placeholders always block readiness. Declared placeholders
require externally supplied, exact-draft `personalization` review evidence proving
resolution, followed by successful preview/test receipts with structured `EmailLoweringEvidence`. Each binds an issuer, receipt reference/digest, contract identity/digest, provider/connection/account, connector revision, lowering profile, sender, draft, template mapping, submitted/observed/rendered digests, token coverage, missing-value behavior and covered snapshot. A boolean alone is insufficient. Without that evidence they remain unresolved and
blocked. Values never enter Creator: the host resolves them outside this package
and refuses missing required values. Evidence authenticity and complete snapshot
coverage authenticity must be verified by the runtime under the public lowering contract. Creator checks the supplied coverage and context equalities. The fake renderer refuses all personalization tokens; it never claims copied placeholders are resolved.

Production preparation requires a current nonempty, unchanged audience snapshot,
matching consent/suppression digests, ready review, successful preview and a test
receipt for a separate test audience. A preview may bind the exact production snapshot; only a test-send audience must differ. Test preparation uses a test-only snapshot
and does not require a previous test-send receipt. Schedule intent must be in the
future and within snapshot validity. Runtime must recheck freshness and drift at
dispatch; Creator never evaluates a trigger or schedules work.

## Exact approval and separate effects

`EmailDeliveryPackage.material` includes the full draft and its binding, subject,
preheader, HTML/plain-text and manifest digests, sender/reply-to references,
compliance, audience summary, tracking, schedule intent, campaign/sequence revision,
review and preview/test evidence, campaign release, execution context and template mapping digest. `approval_digest` is the RFC 8785 digest of that
material. It is an approval target, not an approval receipt.

An operation proposal separately binds editorial effect intent, public Zeocore
operation identity/version/schema digest, delivery reference and approval digest,
sequence revision, exact audience, remote target/revision and migration policy
where applicable. Its own approval digest is RFC 8785 over `{material, idempotency_key}`. The execution context inside material namespaces the logical operation. Changing a retry key requires new approval and creates a different receipt identity.
Use separate identities and approvals for create/update draft, test send, schedule,
immediate broadcast, provision a sequence revision, activate, enrol, pause, cancel, retire and migrate-existing-enrollees. Activation does
not enrol anyone; test success does not approve production; later or larger
audiences require new proposals. Remote update/cancel/pause/retire intents require
an opaque target, observed remote revision digest and normalized `EmailRemoteReceipt` binding issuer, operation, release and exact execution context. Activation also requires the exact provisioned sequence receipt. Cancellation accepts only a scheduling receipt; update accepts only a draft receipt. Both bind `originating_operation` and `target_delivery`, and proposal preparation receives the complete originating proposal. The receipt operation and originating proposal must match exactly. Cancellation cannot name another delivery; draft updates may supply new content only for the same logical message as the target. Cancellation does not require an expired audience or old preview proof to become fresh again.

`creator.propose_email_operation@4.0.0` and `services.email_marketing.propose_operation` inspect the actual release, package and sequence. New content effects re-run delivery preparation; cancellation validates its historical target without reauthorizing a send. They enforce exact package/audience/context bindings and schedule semantics, and check enrolment policy and both proposal/resolution times against the enrolment window. The capability does not
certify support, inspect a provider account, validate a human authorization or
execute anything. At the handoff the host must resolve every digest-bound artifact,
check stored revision uniqueness and the receipt-to-provider-object mapping, authenticate evidence issuers and contract digests, recheck audience authorization/freshness/drift at dispatch, resolve the public operation
contract, refuse unsupported semantics, and obtain fresh effect authority.

A sequence revision has unique stable step IDs and contiguous ordinals. Editing
through `plan_email_sequence` requires the previous revision and increments it.
A separate `provision_sequence_revision` operation binds the exact revision and returns the normalized receipt required for activation. Provisioning cannot activate or enrol anyone. The fake lifecycle produces that receipt through an approved simulated operation; it is no longer supplied out of thin air. Existing enrollees retain their original revision by default. Migration requires
a separate `migrate_existing_enrollees` effect containing source and target sequence revisions, an exact enrollee snapshot, an explicit policy, and a retain/skip/restart disposition for every source step. The source receipt, provisioned target receipt, and target previous-revision binding must agree. Source kind/sequence and target kind/sequence/context/outcome are checked by direct contract construction as well as the service. Activation and enrolment reject migration material. Runtime determines current remote state and grants separate authority.
Conditional graphs, CRM mutations, lead scoring and arbitrary workflows are
outside the linear v4 model.

## Publication isolation and data handling

All new references include organization, publication, revision and digest. Mixing
publications in a request, nested reference, review, snapshot or assessment is
rejected. Shared provider accounts and source material confer no audience-sharing
permission. Cross-promotion requires an explicit publication-scoped policy and a
separately resolved snapshot. Caller-supplied profiles hold Rasa, Prof Rod and
Zero Employee strategy outside the package.

Contracts have no subscriber email/name/contact-ID/property fields, reject extra
fields, and reject email-address-shaped prose. This is a structural guard, not a
universal PII detector: hosts must prevent subscriber records, private identities,
tracking values and provider response bodies from entering editorial text or
opaque references. Links use HTTPS without userinfo. Ordinary query parameters and fragments (including video IDs) are allowed; known tracking/subscriber parameter families are refused. This denylist is not a universal detector of encoded private data. Tracking remains a policy reference applied outside Creator.

Capability failures return a fixed safe code and an allowlisted refusal reason for known domain errors. Unknown validation and injected exception bodies remain opaque.
Pydantic's raw `ValidationError.errors()` can contain original input; never persist
it. Validate before durable logging and retain only safe error classifications.
Digest equality proves integrity, not consent, evidence authenticity, publication
ownership or human approval; those attestations are host responsibilities.

## Offline proof

```console
python -m zeo_creator.examples.email_marketing
# Compact three-publication workflow:
python -m zeo_creator.reference.email_workflow
```

The compact `email_workflow` runs all nine capabilities for three isolated publications,
with four messages and one three-step sequence each. `examples/email_marketing.py`
and installed `python -m zeo_creator.reference.email_program_suite` widen this to eight
separate bounded programs: Rasa weekly newsletter and learning nurture; Prof Rod weekly
newsletter, lead-magnet welcome and membership; Zero Employee weekly newsletter,
orientation and product interest. The caller supplies sanitized identities and objectives;
these examples contain no private brand strategy. Every program includes matching
HTML/plain text, a campaign release, test and production preparation, and a partial assessment.
The effect-family harness exercises all twelve distinct intents through thirteen operations per program: it provisions both source and target sequence revisions and consumes the returned receipts during activation and migration. There are 104 approved simulated operations across eight programs.
These are orchestration proofs, not editorial or provider acceptance verdicts.

`SimulatedEmailHost` demonstrates logical idempotency, conflicting reuse refusal
and ambiguous-outcome reconciliation without resubmission. It is a process-local
conformance harness, not a production journal. Provider transformations produce
`needs_review`. No account, credential, recipient identity, network or live effect
is involved, and the example's simulated approvals are not human approvals.

Schemas are available through `zeo-creator contracts export`. Wheel resources under
`zeo_creator/reference_artifacts` include examples, request/response schemas,
canonical digest vectors and documentation. JavaScript independently verifies the
Python-generated canonical vector bytes and SHA-256 values.

## Public Zeocore integration dependency

Creator pins Zeocore 0.18.0 with its shared Runtime host. The host can invoke
Creator's supplied-input email capabilities; it does not turn Creator proposals
into authenticated provider execution. Creator references caller-selected public
operation identities and does not define executable provider operations or copy
HubSpot/Kit request bodies. The example uses clearly marked `example.email` identities.

Live interoperability remains unverified until the shared email contract and
actual provider lowering are integrated and qualified with this package. A production host must not treat the fake shapes
or example operation IDs as a connector protocol. Lowering must record Creator
artifact/revision/digest, connector revision, submitted and observed payload
digests, transformations/refusals, remote references, idempotency and safe ambiguity.
Unsupported sequence semantics require refusal. Ambiguous results require
reconciliation before any retry.

## Assessment boundaries

Each assessment persists its expected metric set, exact observation window and an
`EmailMeasurementPopulation` containing the exact release and expected confirmed operation
receipts supplied by Runtime/Newsroom. Normalized receipts identify their delivery/message
or sequence. Completeness requires every released message to be represented and every
expected operation × metric cell to have qualified observations. Omitting an operation
for a second released message cannot make the release complete. Observations outside the
declared receipt population are rejected. Multiple operations for one message each need
coverage. The explicit aggregation policy is `per_operation_no_pooling`: values remain
per operation, without silently summing overlapping recipients or incompatible metrics.

Every observation must bind a confirmed normalized operation receipt, provider/connection
and campaign release. An assessment accepts a single aggregate cohort and does not pool
providers or connections. Units are `count`, `rate`, or `currency`; rates must equal their
explicit numerator/denominator. Missing population cells, conflicting values, incomplete
coverage or unreliable observations prevent qualified completeness. Qualitative stopping
conditions remain `human_needed`; Creator does not execute a runtime stop.

## Personalized test and production ordering

A personalized message requires audience-specific external evidence twice:

1. Resolve tokens against the test snapshot outside Creator and supply qualified lowering evidence.
2. Review using that test coverage, prepare the test package with its preview, and authorize a separate test operation.
3. Resolve and render against the production snapshot outside Creator using the same execution context and template mapping.
4. Produce a second editorial review using production coverage, then prepare production with its preview plus the prior test-send evidence.

Reusing the test review for production fails because its snapshot coverage differs.
The regression walkthrough supplies digest-bound external evidence without subscriber
values; it tests consumption of that evidence, not the truth of a provider rendering.
The fake renderer still refuses personalized drafts. Runtime must authenticate issuers
and verify the real mapping/render/snapshot coverage before authorizing effects.

## Email contract migration and release policy

The PyPI package is `zeocreator==0.6.0`; its nine email capabilities and durable email artifacts use
major version 4. Published email v1, v2 and v3 schemas remain byte-for-byte available for
audit. Their preparation APIs are retired from discovery; the twenty original non-email
capabilities remain unchanged. This explicitly affirms the earlier email v1 retirement:
these email families existed only as unreleased development commits, and unsafe approvals
cannot carry forward. Version 0.5.3 is the first PyPI release; it does not make a
1.x API stability promise or establish authenticated provider interoperability.

Rebuild current campaign/message/sequence artifacts, finalize a release with a fully
coordinated CTA set, obtain current audience-specific proof evidence, provision sequence
revisions explicitly, and prepare new effect approvals. Mutations now require the originating
proposal and exact target delivery; assessments require a declared operation population.
The new required provenance fields and changed review semantics receive a new major version
rather than silently changing schemas already on main.

## Verification cost

`current()` validates each root graph once through Pydantic, including nested digests,
scopes and type constraints. It rejects silent normalization/repair and unsafe copies;
it does not recursively JSON-roundtrip every descendant again. There is no process-global
trust cache. The full eight-program example remains in `make verify`, executed in process
without a hardware-dependent per-example deadline. CI retains a fifteen-minute overall
job bound. Regression tests prove both the single-root validation path and rejection of
nested corruption with a recomputed ancestor digest.

## Newsletter compatibility

Existing `AudienceSelection`, `NewsletterIssuePlan`, newsletter draft/review and
generic publication/performance v1 schemas remain byte-for-byte unchanged.
`PlanEmailMessageRequest.newsletter` provides an explicit specialization bridge:
select an existing subject and preheader variant, retain the issue's audience and
consent/suppression references, and supply the new message directions, compliance
and scoped evidence. The resulting plan binds the original newsletter revision.
No old schema is silently reinterpreted.

Historical provider integration work includes Zeocore HubSpot PR 53, Kit PR 54
and follow-up PR 55 at `e2b55aa6b1751afb95614e7b5cbab9f339f5f9e6`.
Creator now installs released Zeocore 0.18.0. Those provider changes and the
shared host do not by themselves establish completed Creator/Runtime email
wiring or authenticated live interoperability.


## Rendering an email body

`zeo_creator.rendering.render_email_body` turns structured blocks into an
accessible HTML **fragment** for a template's content slot, plus its plain-text
twin. It never produces a full document: the template owns the frame, brand
styling and footer.

```python
from zeo_creator.rendering import BodyBlock, BodyLink, render_email_body

body = render_email_body(
    language="en",
    preheader="Three releases this week",
    blocks=(
        BodyBlock(
            heading="What changed",
            paragraphs=("Three releases shipped.",),
            links=(BodyLink(label="Read the notes", url="https://example.org/notes"),),
        ),
    ),
)
```

- **Escaping:** every text node and attribute is escaped. Braces become `&#123;` and `&#125;`, so a template language that evaluates the slot, such as HubSpot's HubL, never sees `{{ }}` from the copy. The plain text keeps the braces, so don't feed it to a template engine.
- **The wrapper:** it declares `lang` (a BCP 47 tag) and `dir`, which must be `ltr` or `rtl`.
- **Structure:** headings are `h2`, and text is `p`.
- **Links:** they follow the same rule as `EmailLink`: an absolute https URL with no userinfo, template braces, tracking or subscriber parameters, and no control characters, at most 2048 characters. So the fragment never carries a link the delivery manifest would refuse. A label, including a linked heading, must describe its target, never repeat the URL.
- **Images:** they need alternative text unless marked decorative, and they scale to the column.
- **Plain text:** it carries every heading, every informative image's alternative text (`Image: ...`), every paragraph, and every link and heading link as `label: url`.
- **Digests:** `html_digest` and `plain_text_digest` are computed exactly as `EmailDeliveryMaterial` computes them. So the result feeds a `NewsletterIssueDraft` or an email draft unchanged.

The renderer applies no voice, lexicon or visual style. It never maps to a provider's draft format: that mapping belongs to the runner's adapter.

## Receipt results and lifecycle preconditions

Email v4 replaces independent optional receipt fields with a required `result`, a
JSON-Schema/Pydantic union discriminated by `kind`. `draft`, `scheduled_broadcast`,
`broadcast`, `test_send` and `cancelled_broadcast` carry exact delivery, message-plan
and audience-snapshot bindings. `sequence_revision` carries an exact sequence binding,
effect intent and lifecycle state; only enrolment/migration carry an audience. Result
variants reject unrelated fields. Each result binds its normalized effect intent;
test results require test audiences and broadcast results require production audiences.
Receipt audience provider/connection must match its execution context. Preview evidence
remains a separate proof contract and cannot masquerade as a remote operation receipt.

The receipt's `operation` binds the originating Creator proposal; `result.intent`
and its audience/state describe that operation's normalized outcome. The synthetic
normalizer derives these fields from the actual proposal and package and refuses a
caller-supplied contradictory kind. Runtime must authenticate the receipt and verify
all those claims against the real originating operation and provider state. A matching
local digest alone cannot authenticate any of them.

| Proposed effect | Required prior state | Confirmed result state |
| --- | --- | --- |
| Provision revision | No prior remote target | provisioned |
| Activate revision | provisioned | active |
| Enrol snapshot | active | active |
| Pause future steps | active | paused |
| Retire revision | active or paused | retired |
| Migrate existing enrollees | paused source and provisioned target | target remains provisioned |

Migration never activates its target. The explicit migration policy and per-step
retain/skip/restart dispositions remain required; later activation needs its own
proposal and authority. A runtime/provider that cannot retain migrated enrolments
without activating the target must refuse these semantics. The bounded contract has
no resume-paused effect; activation cannot be repurposed as resume or reactivation.
Retries reuse the same logical operation, rather than creating another activation.
Current remote state, revocation and stale receipt reconciliation remain runtime checks.

## Metric applicability

A message-bound expected population entry must be a confirmed production `broadcast`
result from `send_broadcast`. Draft, scheduled, test, cancelled, provisioned, activated,
paused, retired and migrated results cannot establish delivery or engagement metrics.
A test audience cannot satisfy production coverage, even with a full observation matrix.

| Eligible operation result | Admissible metrics |
| --- | --- |
| Production broadcast | attempted, accepted, delivered, deferred, bounced, complained, unsubscribed, opened, unique_link_clicks, cta_conversions, campaign_conversion, attributed_revenue |
| Production enrolment | sequence_enrolments, step_completion, step_exit |

Observations reject inadmissible pairs during direct construction. The population rejects
nonmeasurable operations. Its expected matrix contains each operation's applicable metric
cells only; a requested metric with no observations still leaves an explicit gap. Every
released message still needs its own production broadcast coverage, so sequence aggregates
cannot silently cover missing messages. No values are pooled across operations. Provider
definitions, retrieval provenance, observation windows, coverage, reliability and attribution
qualifications remain required; a confirmed broadcast receipt alone proves no delivered count.

Campaign and message CTA plans require unique CTA and CTA-link identities and exactly one
primary CTA. Message link manifests also require unique link identities. Release coordination
compares identity-keyed CTA definitions; the same identity may recur unchanged across messages,
but conflicting definitions and undeclared/unused identities refuse during construction.

For v3-to-v4 migration, rebuild artifacts and obtain receipts with explicit result, effect,
audience and lifecycle evidence. Never infer production status or lifecycle state merely
from a legacy receipt kind, and never relabel a historical approval. Published v3 schemas
remain frozen for audit. This is an explicit breaking development-contract migration.

For receipt ingestion, the exact shared result schema and portable host validation
cases, see [shared receipt conformance](email-receipt-conformance.md).
