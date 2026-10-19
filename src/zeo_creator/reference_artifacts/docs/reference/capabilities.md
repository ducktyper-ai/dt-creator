# Capability catalog

The twenty original capabilities retain `1.0.0`; the nine email capabilities use
`4.0.0`; `creator.evaluate_rubric` is `1.0.0`. Each manifest includes JSON request
and response schemas, effects, requirements, examples, projections, and typed
error codes.

| Capability | Input focus | Output | Effect |
|---|---|---|---|
| `creator.research_synthesis@1.0.0` | Publication, research window, evidence queries | `ResearchSynthesis` | Read |
| `creator.extract_editorial_signals@1.0.0` | Normalized source observations | Editorial signals | Input-only read |
| `creator.update_story_revisions@1.0.0` | Signals and prior immutable revisions | Story revisions | Input-only read |
| `creator.build_story_dossier@1.0.0` | One story revision and prior coverage | `StoryDossier` | Input-only read |
| `creator.plan_editorial_agenda@1.0.0` | Dossiers, desk, coverage window, slots | `EditorialAgenda` | Input-only read |
| `creator.plan_edition@1.0.0` | Agenda, publication window, update policy | `EditionPlan` | Input-only read |
| `creator.plan_content_portfolio@1.0.0` | Syntheses, objectives, history, requirements, planning window | `ContentPortfolioPlan` | Input-only read |
| `creator.create_content_brief@1.0.0` | Assignment, synthesis, profile, creative direction | `ContentBrief` | Input-only read |
| `creator.identify_engagement_opportunities@1.0.0` | Conversation, persona, evidence, expiry | `EngagementOpportunity` | Input-only read |
| `creator.compose_commentary@1.0.0` | Opportunity and conversation | `CommentaryDraft` | Input-only read |
| `creator.review_commentary@1.0.0` | Draft, context, position and experience refs | `CommentaryReview` | Input-only read |
| `creator.plan_newsletter_issue@1.0.0` | Edition, dossiers, audience policy refs | `NewsletterIssuePlan` | Input-only read |
| `creator.compose_newsletter_issue@1.0.0` | Accepted issue plan and dossiers | HTML/plain-text draft | Input-only read |
| `creator.review_newsletter_issue@1.0.0` | Plan and draft | `NewsletterEditorialReview` | Input-only read |
| `creator.compose_news_article@1.0.0` | Article plan and frozen dossiers | `NewsArticleDraft` | Input-only read |
| `creator.review_news_article@1.0.0` | Plan, draft and qualified-human review ref | `EditorialReview` | Input-only read |
| `creator.prepare_correction@1.0.0` | Reviewed article and corrected claims | `CorrectionNotice` | Input-only read |
| `creator.validate_delivery@1.0.0` | Brief, artifact manifest, profile, synthesis, channel plan | `DeliveryReviewBundle` | Input-only read |
| `creator.evaluate_rubric@1.0.0` | A review rubric, scorecards, the subject and its text (unreleased) | `RubricEvaluation` | Input-only read |
| `creator.prepare_distribution@1.0.0` | Accepted review and exact channel plan | Publication proposals | Input-only read |
| `creator.assess_performance@1.0.0` | Profile, metric queries, objective | Performance assessment | Read |
| `creator.plan_email_campaign@4.0.0` | Supplied email artifacts | EmailCampaignPlan | Input-only read |
| `creator.finalize_email_campaign@4.0.0` | Exact campaign, messages and sequences | EmailCampaignRelease | Input-only read |
| `creator.propose_email_operation@4.0.0` | Exact effect intent and originating evidence | ProposedEmailOperation | Input-only read |
| `creator.plan_email_sequence@4.0.0` | Supplied email artifacts | EmailSequencePlan | Input-only read |
| `creator.plan_email_message@4.0.0` | Supplied email artifacts | EmailMessagePlan | Input-only read |
| `creator.compose_email_message@4.0.0` | Supplied email artifacts | EmailMessageDraft | Input-only read |
| `creator.review_email_message@4.0.0` | Supplied email artifacts | EmailEditorialReview | Input-only read |
| `creator.prepare_email_delivery@4.0.0` | Supplied email artifacts | EmailDeliveryPackage | Input-only read |
| `creator.assess_email_program@4.0.0` | Supplied email artifacts | EmailProgramAssessment | Input-only read |

Use `zeo-creator capabilities` for canonical manifests or
`zeo-creator capabilities --projection openai` for function-tool projections.

Zeocore 0.9 requires every manifest to carry at least one effect kind. Pure
transformations therefore conservatively declare `read`; the email family also
carries the `pure` tag and has no required acquisition services or network access. This
compatibility boundary can be removed if Zeocore gains an explicit pure effect.

Workflow composition, scheduling, retries, approval waits, and effect authorization are
runtime concerns; the package deliberately exposes no monolithic workflow.

The query-based research and performance v1 capabilities are retained for legacy
compatibility. Canonical email assessment uses already-collected observations in
`assess_email_program`; never inject a live connector into that capability.

## Review rubrics (unreleased)

`creator.evaluate_rubric@1.0.0` applies any `ReviewRubric` to `RubricScorecard`s. Creator ships the
shape and the pure engine. It holds no rubric instance, scorer, lexicon, persona or profile: those
belong to the runner that supplies the rubric.

- **A rubric is data:** criteria are either *scored* (`max_points`, `floor`, `weight`, all integers)
  or *must_pass*. Each carries a `rule_ref`. A rubric declares its languages (BCP 47) and refuses
  a scorecard in another.
- **Floors bind, and averages never excuse one.** Every floor and every must-pass is checked on
  that criterion's raw points. Weights only move the weighted total, which is reported as an exact
  ratio. An aggregate floor, if declared, is compared under one declared rounding.
- **A failing or unknown score carries typed evidence:** `text_quote` (it must occur in the subject's
  text or the named block), `artifact_region`, `missing_element` or `corpus_match`. A failure with no
  evidence is refused, and no quote is ever invented for a non-text failure.
- **Unknown fails closed:** a score may be `unknown` (with a reason and evidence), and an unknown or
  missing score never meets a floor or a must-pass.
- **A human re-scoring is a separate scorecard** that references the primary one by id and digest. It
  must still meet the floor, a human failure always stands, and a criterion backed by a producer check
  cannot be re-scored by a person.
- **Raise, never lower.** A `masthead` rubric must name its house base (`base_rubric_ref`). The engine
  refuses it if a base criterion is missing or changes kind or `max_points`, if a floor or the aggregate
  floor is lower, if the aggregate rounding differs, if a weight changes without being declared, or if
  the base is missing, its digest does not match, or it is not in the supported list the caller gives.
  A `house` rubric may name a base too, with the same rules.
