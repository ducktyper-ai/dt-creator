# Build a content portfolio

This tutorial follows the credential-free reference workflow. Two example
publications retain separate profiles, histories, evidence, objectives, and
approval scopes throughout the pipeline.

## 1. Synthesize evidence per publication

Invoke `creator.research_synthesis@1.0.0` independently for each publication.
The injected `EvidenceSourcePort` receives provider-neutral queries and returns
provenance-rich `EvidenceItem` values. Missing context fails closed.

Never combine evidence first and attempt to reconstruct publication scope later.

## 2. Plan for an explicit window

The caller provides a planning window plus content requirements:

```python
PortfolioConstraints(
    requirements=(
        ContentRequirement(content_kind="article", quantity=1),
        ContentRequirement(content_kind="video.short", quantity=1),
        ContentRequirement(content_kind="image.carousel", quantity=1),
        ContentRequirement(content_kind="newsletter.issue", quantity=1),
    )
)
```

Content kinds are qualified identifiers, not a closed enum. Your organization
can choose any cadence and can use private qualified identifiers without adding
them to this package.

## 3. Create producer-neutral briefs

Invoke `creator.create_content_brief@1.0.0` once per assignment. Each
`ContentBrief` carries creator intent, a standard content document, evidence
claims, brand references, target channels, and declarative attestation
requirements. Optional producer extensions remain opaque and digest-bound.

## 4. Produce an artifact bundle

Pass the brief to an external adapter. A producer can return one artifact or a
bundle—for example HTML and plain text, video and captions, or a carousel of
images. It reports those outputs in `ArtifactManifest`, including byte lengths,
digests, retrieval proofs, claim IDs, and typed attestations.

## 5. Validate delivery

`creator.validate_delivery@1.0.0` verifies:

- brief, manifest, organization, publication, revision, and digest identity;
- artifact-byte digest proofs;
- required attestations declared by the brief;
- evidence-claim provenance;
- prohibited language and brand profile binding; and
- proposed destination constraints.

Missing required evidence or an empty extracted-text proof fails closed.

## 6. Prepare distribution

The review's approval digest binds the brief, manifest, publication payload,
destination accounts, and schedule. `creator.prepare_distribution@1.0.0`
creates idempotent proposals but performs no provider write.

## 7. Assess performance separately

After an authorized runtime executes proposals, invoke
`creator.assess_performance@1.0.0` per publication. Metric observations carry
provider definitions, units, attribution windows, baselines, targets, and
normalized rates. The assessment reports hypotheses rather than invented causes.

After [installation](../getting-started/installation.md), validate the packaged
reference portfolio from any directory:

```console
python -m zeo_creator.examples.complete_content_portfolio
```

In a source checkout, `make reference` rebuilds the fixtures from the deterministic
strategies. The installed example validates the bundled artifacts without regenerating them.

Inspect the generated JSON in
[`reference/examples`](https://github.com/ducktyper-ai/dt-creator/tree/main/reference/examples).
