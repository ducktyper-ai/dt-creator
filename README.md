# Education core prototype

Unpublished `0.1.0-alpha.2` contract prototype. Pure ESM, Node22+, no dependencies,
service/filesystem access or Astro-version assumption. This is the first small
piece of the operator's shared Astro education foundation, not a complete framework.

Astro collection adapters project public metadata through
`projectPublicInventory(site, documents, {selectPublication})` for discovery,
SEO, feeds, search and OG targets. Trusted site-owned code selects eligibility and
returns `null` or public publication metadata; exact UTC timestamps are preserved.
No universal clock or date-only schedule is inferred. The earlier
`compilePublicInventory(site, documents, {asOf: 'YYYY-MM-DD'})` remains an explicit
date-only prototype policy and must not implement Rasa's request-time casebook clock.
Draft, retired, review, member and paid documents are excluded;
unknown input properties and all bodies are dropped. Public course teasers must
be separately authored public documents; this module does not release paid bodies.

Run `node --test packages/education-core/test/*.test.mjs` from the repository.
Tests exercise ProfRod and Rasa origin/route policies, privacy exclusions,
canonical and duplicate-route failures, dates and immutable deterministic output.
These fixtures are not parity tests of the actual site adapters. Layouts, Astro
integration, course graph validation, OG rendering, gate orchestration, entitlement
services, publishing and deployment remain follow-on work. Existing five-file
homepage build input is unchanged; this package is not shipped by that build.

See the exact design in the records repository at
`81c238378f1fc19cc24900a5ba70b8684917fe1c`,
`projects/zeo-site/design/shared-astro-education-v1/architecture.md`.
