# Education core prototype

Unpublished `0.1.0-alpha.1` contract prototype. Pure ESM, Node22+, no dependencies,
service/filesystem access or Astro-version assumption. This is the first small
piece of the operator's shared Astro education foundation, not a complete framework.

Astro collection adapters can project eligible public metadata through
`compilePublicInventory(site, documents, {asOf: 'YYYY-MM-DD'})` for discovery,
SEO, feeds, search and OG targets. The explicit time makes publication eligibility
reproducible. Draft, retired, review, member and paid documents are excluded;
unknown input properties and all bodies are dropped. Public course teasers must
be separately authored public documents; this module does not release paid bodies.

Run `node --test packages/education-core/test/core.test.mjs` from the repository.
Tests exercise ProfRod and Rasa origin/route policies, privacy exclusions,
canonical and duplicate-route failures, dates and immutable deterministic output.
These fixtures are not parity tests of the actual site adapters. Layouts, Astro
integration, course graph validation, OG rendering, gate orchestration, entitlement
services, publishing and deployment remain follow-on work. Existing five-file
homepage build input is unchanged; this package is not shipped by that build.

See the exact design in the records repository at
`81c238378f1fc19cc24900a5ba70b8684917fe1c`,
`projects/zeo-site/design/shared-astro-education-v1/architecture.md`.
