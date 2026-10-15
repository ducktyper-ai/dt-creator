# Education core prototype

Unpublished `0.1.0-alpha.4` contract prototype. Pure ESM, Node22+, no dependencies,
service/filesystem access or Astro-version assumption. This is the first small
piece of the operator's shared Astro education foundation, not a complete framework.

**Labelled spike only. Do not merge this package into zeo-site main or publish it.**
Council requests changes and Architect must select the shared source home. Actual
ProfRod/Rasa schemas/adapters, typed installable release, retired URL disposition
and post-build privacy scans remain prerequisites. No production safety or adoption
is inferred from the source-function probes or this spike's gate.

Astro collection adapters project public metadata through
`projectPublicInventory(site, documents, {now, selectPublication})` for discovery,
SEO, feeds, search and OG targets. Every published public candidate requires a
source-adapter-derived UTC `availableAt`; the core refuses missing derivation even
if a callback would hide it. The finite explicit `now` reaches the frozen-copy
selector and is returned as `evaluatedAt` alongside `entries`. A selector returning
metadata cannot publish before the source availability instant. Display dates stay
metadata; `updatedAt`, when supplied, is an exact UTC instant bounded by availability
and evaluation. No universal clock or UTC-day schedule is inferred. Pure prototype
derivations in `policies.mjs` preserve UTC or London-date semantics including DST;
they are not replacements for the real site schemas. Undated/deploy-time entries
without an accepted deployment instant remain unsupported, not assigned a fake date.
The earlier
`compilePublicInventory(site, documents, {asOf: 'YYYY-MM-DD'})` remains an explicit
date-only prototype policy and must not implement Rasa's request-time casebook clock.
Its UTC-midnight interpretation also is not ProfRod's London-date policy.

Clock supply stays with trusted platform adapters: accepted Rasa middleware takes
one server `Date.now()` snapshot into `locals.publicationNow`; a Netlify adapter
must pass that same value to all projections. A ProfRod/Node adapter must obtain
one trusted owner-policy request clock and pass its milliseconds explicitly;
the source helper's `PROFROD_PUBLICATION_CLOCK` test/configuration override is not
a user-controlled request clock or an automatic production grant. Real profiles
must qualify clock provenance and test-override handling before adoption. Pure
library functions do not read global time or request/query/env overrides.

Trusted `defineSite` configuration may declare `extensionKinds` as unique names.
Document data cannot register a kind. Actual extension schemas and public payload
validation remain owner-adapter responsibilities, not a bypass for private access.
Draft, retired, review, member and paid documents are excluded;
unknown input properties and all bodies are dropped. Public course teasers must
be separately authored public documents; this module does not release paid bodies.

Run `node --test packages/education-core/test/*.test.mjs` from the repository;
`make verify` now includes this suite. All routable entries reserve valid paths
before any publication callback, including future/draft/member/paid entries.
The spike accepts ASCII route segments only and rejects case-only collisions;
broader route-policy support requires source-owner review. Callbacks receive a
deep-frozen clone; output text remains untrusted and needs context-specific escaping.
Tests exercise ProfRod and Rasa origin/route policies, privacy exclusions,
canonical and duplicate-route failures, dates and immutable deterministic output.
These fixtures are not parity tests of the actual site adapters. Layouts, Astro
integration, course graph validation, OG rendering, gate orchestration, entitlement
services, publishing and deployment remain follow-on work. Existing five-file
homepage build input is unchanged; this package is not shipped by that build.

Optional read-only source probes accept owner-provided exact source inputs:
`node packages/education-core/tools/upstream-rasa-parity.mjs /existing/rasa/repo`
and `node packages/education-core/tools/upstream-profrod-parity.mjs /owned/SOW311.tar.gz`.
The Rasa probe reads its fixed accepted git object; the ProfRod probe verifies the
owner archive and all payload hashes without extraction, then tests original
London-clock note selection and DST freshness. These are source-function observations,
not full collection/Netlify/Node/browser or production adoption evidence. They log
the local source head, exact evaluation clock and core input digests; these local
observations are not authenticated CI or receipt-custody evidence.

The original design is retained in the **fork**, not asserted merged into gold, at
`81c238378f1fc19cc24900a5ba70b8684917fe1c`,
`projects/zeo-site/design/shared-astro-education-v1/architecture.md`.
Follow `matorclawson/org-zeroemployeeorg` branch
`zeroemployee/shared-astro-foundation-20261014` for subsequent source-owner mappings,
review corrections and exact-source SOW/evidence references; canonical gold remains
a separate target. This prototype is not consumed by either production site.
