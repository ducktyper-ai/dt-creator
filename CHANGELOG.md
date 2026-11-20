# Changelog

All notable changes to ZEO Creator are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Newest first.

## Status

*Current as of 2026-11-20.*

- **What it is:** ZEO Creator (PyPI `zeocreator`, import `zeo_creator`, command `zeo-creator`) is a Python library of creator-domain operations over Zeocore contracts: research synthesis, editorial planning, content briefs, delivery validation, distribution proposals, email-program contracts, performance assessment, and a generic review rubric. It does pure, deterministic transformation. It owns no credentials, scheduling, provider writes or releases.
- **How alive:** maintained. Last meaningful change 2026-10-30. Current release: 0.6.1 (2026-10-27). Releases so far: 0.5.3, 0.5.4, 0.6.1.
- **Works today:** 30 registered capabilities; the `zeo-creator` command (JSON-lines output, `help --json`, `doctor`, `capabilities`, `contract-schema`, `lint-thread`, `check-length-budgets`); versioned JSON Schemas shipped in the wheel; offline examples; the Zeocore runtime-host provider (Zeocore 0.28.0).
- **Known not to work yet:** no live provider interoperability or effects are claimed (email contracts are provider-neutral and simulated offline); the bundled private `publication-core` package is verified offline only, and its declaration type soundness is not qualified; the command line has no newsletter plan, compose or review commands yet (the capabilities exist in the library); the runtime-provider command still prints its original bytes without `ok`.
- **Check it yourself:** `make verify` (the full gate: release consistency, tests, types, lint, docs, digest vectors, built-wheel checks; run it on a Linux host). `make doctor` checks your prerequisites. Python 3.14 or newer and Node 24 are required.

## Unreleased

### Added
- `zeo-creator check-length-budgets`: a generic word-budget check as a command. The caller supplies every budget; it names each breach and never trims. JSON on stdout; exit 0 within budget, 20 when a budget is broken, 2 for invalid input. Also available as `zeo_creator.services.length_budgets.check_length_budgets`. Output schema `zeocreator.length-budgets/v1`. It is not a capability, so the capability list and the runtime-provider inventory are unchanged. `lint-thread` now shares its input reader; its output is unchanged.
- An illustrative newsletter rubric (`example.newsletter`: five generic scored criteria, an 80-of-100 bar, no criterion under 60%) with example budgets for intro, item and outro sections. It is example data, not a scorer and not production policy.

### Fixed
- Release notes and the release-readiness text now describe 0.6.1 correctly, including that 0.6.0 was never published, with the true test counts.

## 0.6.1 — 2026-10-27

This is the first published release of the 0.6 content. The `v0.6.0` tag was created on 2026-10-13, but its publish run stopped before upload, so 0.6.0 never reached PyPI.

### Changed (breaking for anyone who parses command output)
- Command output follows Zeocore's `cli_protocol` 1. Every command except `runtime-provider` prints exactly one JSON line on stdout, carrying `ok` and a `schema` id such as `zeocreator.<thing>/v1`. Lists are wrapped (`capabilities` answers `{"ok": true, "capabilities": [...]}`, `contracts list` answers `contracts`, `contract-schema` answers `json_schema`, `--version` carries `cli_protocol`). The tables are gone; `--json` is still accepted and changes nothing. A usage error prints usage on stderr and an `invalid_request` result on stdout.
- Exit codes: 0 success, 1 internal error (no detail printed), 2 invalid input, 20 a failed check. A failing `doctor` check now exits 20, not 1.
- Requires `zeocore[runtime-host]==0.28.0` (was 0.11.0). The `doctor` check is named `zeocore_0_28_0`.
- The repository, documentation and package-metadata links point at the repository's new home after it moved and was renamed. The PyPI name, the import, the command and every schema id are unchanged.
- Builds can write outside the checkout through `DIST_DIR` and `SITE_DIR`.
- Dropped the direct `rich` dependency; Typer still installs it.
- The publish path verifies with Node 24 (the 0.6.0 run stopped for lack of it), and a shared verify-and-build step also runs, without uploading, on every pull request that touches the release path.

### Added
- 30th capability, `creator.evaluate_rubric@1.0.0`, with the `ReviewRubric` and `RubricScorecard` contracts: a pure, fail-closed rubric engine. It ships the shape and the engine only, with no rubric instance, scorer or persona.
- Thread authoring: `zeo-creator lint-thread` and `zeo_creator.thread_lint`, a deterministic structural linter for numbered post threads (280-character limit counted as NFC code points with URLs as 23, numbering, link dependence, repeated last post, caller-supplied forbidden phrases). It rejects control, ambiguous-space and similar characters and duplicate JSON keys. Output schema `zeocreator.thread-lint/v1`; exit 0 clean, 20 findings, 2 invalid. Ships with a `thread-authoring` skill.
- `zeo-creator help --json`: a machine catalogue of every command, option, exit code and output schema.
- `doctor` lists each failing check with the command that fixes it, under `next`; invalid requests carry a fixed `reason` and a `next` command, never the input.
- `zeo_creator.rendering.render_email_body`: a pure renderer from structured blocks to an accessible, escaped HTML fragment, with a plain-text twin and digests that match `EmailDeliveryMaterial`.
- `make install VERSION=X.Y.Z` installs a published release as a tool and runs `doctor`.
- Shared JCS test vectors and a decision record on bounded Zeocore compatibility; a contributors charter written for agents first.
- A private publication-core package (Node 24, zero dependencies) imported with its history, with contract and failure-path tests in `make verify`; offline archive and index verification for candidates. It is never part of the Python wheel.

### Fixed
- The reference story-revision strategy chains same-topic signals in one batch into successive revisions instead of several unrelated first revisions.
- Signal, revision and dossier capabilities refuse an injected strategy's output that cites a reference that is not an input of the same call.
- Email links refuse a backslash, which browsers treat as a path separator but URL parsers do not, so a link could not show one host and open another.

### Security
- The pull-request smoke job no longer keeps the checkout token in the workspace.

## 0.5.4 — 2026-09-10

### Changed
- Requires the released `zeocore[runtime-host]==0.11.0`.

### Added
- Canonical installed-provider inventory and strict, normalized request helpers; the existing 29-capability factory is exposed to the shared runtime host.
- An offline portfolio invocation example and documentation of exact launch and artifact bindings; all eight installed examples and 135 receipt cases are verified in the gates.

## 0.5.3 — 2026-09-09

First release on PyPI as `zeocreator` (import `zeo_creator`, command `zeo-creator`).

### Added
- Email v4: nine input-only email capabilities, exact receipt validation and 135 portable conformance cases, over the twenty original non-email capabilities.
- Seven runnable examples and their reference data packaged for use without a checkout.
- Tag-bound trusted publishing with full pre-publication verification, exact-version index smoke tests and automatic GitHub releases.
- PyPI installation, migration, quickstart and release documentation.

No live provider interoperability or effects are claimed. Zeocore stays pinned to 0.9.0.

## Development history before the first release (2026-09-05 to 2026-09-09)

These lines were tracked in git only and were not published.

- **0.5.3.dev0 (09-09):** explicit corpus-version selection so legacy exporters cannot overwrite the v1 corpus; clarified when cancellation proposals omit their package.
- **0.5.2.dev0 (09-08):** reject prior receipts whose normalized effect contradicts their proposal; corpus v2 with 135 cases covering every result kind and effect; historical v1 bytes retained.
- **0.5.1.dev0 (09-08):** bind consumed receipts to exact proposals, content, audience and remote targets; export the v4 result union and 36 behavioral cases.
- **0.5.0.dev0 (09-08):** explicit email v4 receipt results (kind, normalized effect, exact audience, lifecycle state); sequence transition rules; unique call-to-action identity.
- **0.4.0.dev0 (09-07):** explicit email v3 schemas; bind cancellation and draft updates to their proposal; delivery-readiness checks; complete-assessment coverage rules.
- **0.3.0.dev0 (09-07):** explicit email v2 contracts with logical operation keys, provenance and acyclic campaign releases; immutable remote receipts.
- **Email inception (09-07):** provider-neutral email campaigns, sequences, messages, reviews, delivery packages and aggregate assessments, with three-publication offline conformance.
- **0.2.0.dev0 (09-05):** hardened evidence lineage, canonical digests and packaging; generic `ContentBrief` and destination-specific distribution contracts; versioned JSON Schemas in the wheel; continuous editorial kernel; commentary, newsletter, journalism, review and correction contracts; twenty capabilities.
- **0.1.0 (09-05):** the first six-capability foundation.
