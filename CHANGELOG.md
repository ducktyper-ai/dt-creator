# Changelog

## Unreleased

- Add the generic review rubric: the `ReviewRubric` and `RubricScorecard` contracts and the pure, fail-closed capability `creator.evaluate_rubric@1.0.0` (the 30th capability; the runtime-provider inventory changes). Creator ships the shape and the engine only: no rubric instance, scorer, lexicon, persona or profile.
- Add `examples/newsletter_rubric.py`: the shared newsletter quality bar as rubric data (relevance, interest, concision, voice, visual quality; 90 of 100 overall, no criterion under 80%) and a deterministic length-budget check. It is example data the caller owns, not a shipped rubric instance, scorer or capability; no model is called.

## 0.6.0 — 2026-10-13 (preparation marker; the release date is set when tagged)

- Add the `thread-authoring` skill (`skills/thread-authoring/SKILL.md`) with `zeo-creator lint-thread` and `zeo_creator.thread_lint`, a deterministic structural linter for a numbered post thread (`thread-draft/1`): 280-character limit counted as NFC code points with URLs as 23, numbering, source outside the posts, link dependence, a repeating last post, and caller-supplied forbidden phrases. It reports what needs a reviewer under `needs_review`. Output schema `zeocreator.thread-lint/v1`; exits 0 clean, 20 findings, 2 invalid. It refuses control, default-ignorable, unassigned and ambiguous-space characters and a post hidden inside another, and rejects duplicate JSON keys. Not a registered capability; the runtime-provider inventory is unchanged.
- Import the five-commit publication-core history without squash, then separately neutralize the private zero-dependency ESM package at `packages/publication-core/`. Its Node 24 contract/export and failure-path tests run in `make verify`; actual Python wheel and sdist checks refuse inclusion of `packages/`. No Python contract/version, provider, npm dependency, release or consumer adoption changes.
- Add `CONTRIBUTING.md`, a contributors charter written for agents first (how to propose, what is welcome, owner-only areas, how to build and submit, response times), linked from `AGENTS.md`.
- Point repository, documentation, badge and package-metadata links at `zeroemployeeorg/zeocreator` and `zeroemployeeorg.github.io/zeocreator` after the repository move; the old GitHub Pages address no longer resolves. Version tags and commit pins are unchanged.
- State the required PyPI trusted publisher and that its current configuration is unverified since the move.
- **CLI output follows Zeocore's `cli_protocol` 1.** Every command except `runtime-provider` prints exactly one JSON line on stdout, the result, which carries `ok`. Lists are wrapped: `capabilities` answers `{"ok": true, "capabilities": [...]}` (or `"tools"` with `--projection openai`), `contracts list` answers `"contracts"`, `contract-schema` answers `"json_schema"`, and `--version` answers `{"ok": true, "zeocreator": ..., "cli_protocol": "1"}`. Every result also names its schema id. The tables are gone; `--json` is still accepted and changes nothing. A usage error prints its usage on stderr and an `invalid_request` result on stdout; running with no command is a usage error.
- **Exit codes follow `cli_protocol` 1** (catch-up: merged in #20 without an entry): a failed `doctor` check exits 20, not 1; 1 is an internal error, with `{"ok": false, "outcome": "internal"}` and no detail; 2 is invalid input.
- `runtime-provider` keeps its canonical bytes, without `ok`, until Runtime confirms a reader for the JSON-lines form; then it changes in one release.
- Add `make install VERSION=X.Y.Z`, which installs a published release as a tool and runs `doctor` (catch-up: merged in #20 without an entry).
- Publishing runs in the GitHub environments `pypi` and `testpypi`, so an upload waits for approval once the environment requires a reviewer.
- Drop the direct `rich` dependency, which the CLI no longer uses; Typer still installs it.
- **Agentic experience (standard v1):** `zeo-creator help --json` is a machine catalogue of every command, option, exit code and output schema id. Every result carries `"schema": "zeocreator.<thing>/v1"`. `contract-schema` now answers the schema under `json_schema` (unreleased rename; `schema` is the id). Shell-completion options are gone.
- `make verify` can write its builds outside the checkout: `DIST_DIR` and `SITE_DIR` (defaults `dist` and `site`) set where `uv build` and `mkdocs` write, and the distribution checks read `ZEOCREATOR_DIST_DIR`.
- **Next steps (standard v1, rules 6 and 7):** `doctor` lists each failing check with the command that fixes it, under `next`. An invalid request carries a fixed `reason` and a `next` command, never the input. The unknown-contract `message` (unreleased) becomes `reason`.
- Email links refuse a backslash, which browsers read as a path separator but URL parsers don't, so a link can't show one host and open another. This applies to `EmailLink` and the body renderer alike.
- Add `zeo_creator.rendering.render_email_body`, a pure renderer from structured blocks to an accessible, escaped HTML fragment for a template slot, with its plain-text twin and digests that match `EmailDeliveryMaterial`.
- **Require `zeocore[runtime-host]==0.18.0`** (was 0.11.0; qualified at 0.15.0 and again at 0.18.0, whose runtime-host-v1 protocol files are byte-identical). Zeocore 0.15.0 made every runtime-host name Creator uses public. `doctor` reports the check as `zeocore_0_18_0`.
- **Fix:** the reference story-revision strategy chains same-topic signals in one batch into successive revisions (1, 2, ...) with `previous_revision_ref` set, instead of several unrelated revision 1s of one story. Reference artifacts and contract digests are unchanged.
- **Fix:** `extract_editorial_signals`, `update_story_revisions` and `build_story_dossier` refuse an injected strategy's output that cites a signal, source, revision, story or lineage reference that is not an input of the same call.
- Add the shared JCS test vectors v1 and wire rule 7 (a digest covers the fully materialized contract), and ADR 0003 on bounded Zeocore compatibility.

## 0.5.4 — 2026-09-10

- Upgrade to the released `zeocore[runtime-host]==0.11.0` dependency.
- Add canonical installed-provider inventory and strict normalized request helpers.
- Expose the existing 29-capability factory to the shared Runtime host.
- Package an offline portfolio invocation example and document exact launch/artifact bindings.
- Exercise the installed host, real Creator planner and refusal paths through a labelled test peer.
- Preserve business schemas, email receipt cases and the boundary to Runtime authority.
- Verify all eight installed examples and 135 receipt cases in local, CI and index smoke gates.
- Update PyPI installation, CLI, Runtime host and release documentation for 0.5.4.

## 0.5.3 — 2026-09-09

- First PyPI release as `zeocreator`; preserve the `zeo_creator` import and `zeo-creator` CLI.
- Ship the independently accepted email v4 implementation: nine input-only email capabilities, exact receipt validation and 135 portable conformance cases.
- Preserve all prior schema and corpus bytes and the twenty original non-email capabilities.
- Package all seven runnable examples and their reference data for use without a checkout.
- Add PyPI installation, migration, quickstart and release documentation plus complete release notes.
- Add tag-bound OIDC publishing, full pre-publication verification, exact-version index smoke tests and automatic GitHub Releases following Zeocore.
- Keep Zeocore pinned to 0.9.0; no live HubSpot/Kit interoperability or effects are claimed.

The entries below record the earlier Git-only development history.

## 0.5.3.dev0 — 2026-09-09

- Require explicit corpus version selection so legacy exporters cannot overwrite v1 with v2 data.
- Add exporter v8 for the current build while retaining historical script and corpus bytes.
- Clarify when cancellation proposal preparation must omit its package argument.
- Preserve the reviewed v4 contracts and all 135 v2 conformance cases unchanged.

## 0.5.2.dev0 — 2026-09-08

- Reject prior receipts whose normalized draft effect contradicts their originating proposal.
- Preserve the specific safe refusal through proposal capability results.
- Publish corpus v2 with 135 cases covering every result kind/effect and portable binding substitutions.
- Include proposal and package schemas; retain the historical v1 corpus and every existing schema byte.
- Prove the reviewers' lax and partial validators pass v1 but fail v2. No live effects or release.

## 0.5.1.dev0 — 2026-09-08

- Bind consumed normalized receipts to exact proposals, content, audience and remote targets.
- Correct simulated migration receipts to return the target sequence object.
- Export the existing v4 result union and 36 portable behavioral conformance cases.
- Verify conformance from the installed wheel; retain every prior schema byte.
- Preserve uncertain outcomes and historical evidence without authorizing effects.

## 0.5.0.dev0

- Introduce explicit email v4 receipt results with a kind discriminator, normalized effect,
  exact audience and lifecycle state; preserve every existing v1/v2/v3 schema byte.
- Enforce sequence transition preconditions and prevent migration from activating its target.
- Restrict production metric observations/populations to applicable broadcast or enrolment results.
- Validate CTA identity uniqueness and one primary at direct contract construction and release coordination.
- Return safe stale_email_artifact classification for nested validation failures.
- Add direct-construction and full lifecycle/metric matrix regression coverage. No live effects or PyPI release.

## 0.4.0.dev0 — 2026-09-07

- Introduce explicit email v3 schemas while preserving all published v1/v2 schemas.
- Close sequence provisioning and activation provenance, including migration target receipts.
- Bind cancellation and draft updates to the originating proposal and target delivery.
- Move preview/test checks exclusively to delivery readiness; coordinate all campaign CTAs.
- Require expected operation and release-message coverage for complete assessments.
- Validate root graphs once, preserve nested integrity checks, and remove the example's hardware-dependent deadline.
- Exercise audience-specific personalized review ordering with supplied evidence.


## 0.3.0.dev0 — 2026-09-07

- Replace email preparation APIs with explicit v2 contracts; preserve all v1 schemas.
- Bind logical operation keys, provider context, actual package material and acyclic campaign releases before approval.
- Require lowering provenance, immutable remote mutation receipts and explicit per-step migration authority.
- Correct CTA/accessibility review, ordinary query links, preview audience handling and safe refusal reasons.
- Persist assessment expectations and provenance; reject mixed cohorts and qualify conflicts.
- Add reviewer counterexamples and eight independent publication programs with all eleven simulated effects.


All notable changes to ZEO Creator are documented here.

## Development inception — 2026-09-07

- Add versioned provider-neutral email campaigns, linear sequences, messages, reviews,
  audience snapshots, exact delivery packages, effect intents and aggregate assessments.
- Register seven input-only email capabilities alongside all existing v1 capabilities.
- Preserve newsletter schemas and add an explicit common-message specialization path.
- Ship three-publication offline conformance, schemas, digest vectors and documentation
  in the wheel. Live Zeocore email interoperability remains pending its public contract.
- Clarify that Runtime/Newsroom acquire and persist observations before Creator invocation.
- No dependency upgrade, PyPI publication or live provider execution.

## 0.2.0.dev0 — 2026-09-05

- Harden evidence lineage, delivery attestations, canonical digests, timestamps,
  performance semantics, and distribution packaging for product-readiness.
- Replace producer-specific public contracts with `ContentBrief`, extensible
  content kinds, artifact bundles, declarative attestations, and opaque extensions.
- Generalize portfolio planning to explicit windows and caller-supplied quantities.
- Ship versioned JSON Schemas in the wheel with list, inspect, and export commands.
- Replace branded factory fixtures with neutral two-publication examples.
- Rename `DailyPerformanceAssessment` to cadence-neutral `PerformanceAssessment`.
- Replace shared publication payloads with destination-specific distribution
  variants that bind channel, selected artifacts, content, accessibility text,
  optional extensions, and schedules.
- Add RFC 8785 schema digests and an explicit package/capability/schema
  compatibility policy to the bundled contract catalog.
- Add the continuous editorial kernel: source observations, signals, immutable
  story revisions, frozen dossiers, agendas, publication slots, and editions.
- Add provider-neutral commentary, newsletter, journalism, human-review, and
  correction contracts with deterministic reference strategies.
- Expand the registry to twenty independently composable capabilities without
  adding workflow persistence, scheduling, credentials, or publishing authority.

## 0.1.0 — 2026-09-05

- Establish the initial six-capability creator-operations contract foundation.
