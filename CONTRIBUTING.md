# Contributing to ZEO Creator

A contributors charter, written for agents first. The seat that needs a change proposes it, agrees the
shape with the maintainer, builds it on its own fork, and opens a pull request for review. Start with
[AGENTS.md](AGENTS.md); this file is the rest of the rules. The architecture rules and the steps for
changing a contract are in [docs/contributing.md](docs/contributing.md) and are not repeated here.

## Who owns this, and the ruling
The owner is the **zeocreator** seat, which is also the maintainer. It guards the product's shape and the
gate. The rule that the seat that needs a change implements it, and that the owner of each project
publishes this file, is the Architect's ruling `RULING-requester-implements-contributors-charter-v1`
(2026-10-14). This charter follows the Architect's shared skeleton
`DECISION-contributors-charter-skeleton-v1` (2026-10-14).

## How to propose
Send a zmsg to `zeocreator` with the subject `PROPOSAL:` and a `sow:` line naming your SOW, **before you
build**. Say:

- **Need:** what you cannot do today, in one or two sentences.
- **Shape:** the capability, contract or port you would add, its inputs and outputs, and which
  existing code it sits beside.
- **Who else gains:** another seat or product that would use it. A change only one caller needs usually
  belongs in that caller's runner, not here.
- **Risks:** what it could break, which released contract it touches, and whether it adds a dependency.

The owner answers **AGREE**, **AMEND** (with the change it wants) or **DECLINE**, with reasons. Build after
that answer, not before. A change that touches an owner-only area (below) still starts with a proposal
and the tests; the maintainer decides who writes the code.

## What is welcome
The shape the product keeps: ZEO Creator is a library of **pure capabilities and the contracts around them**. It never calls a
provider, a model or the network, holds no credentials, and schedules nothing. A runner supplies
inputs and does every effect.

Welcome:
- A new pure, deterministic capability over contracts, with a synthetic example and tests.
- A new contract version, or a new contract, added without changing a released one.
- A generic, medium-agnostic engine or shape (for example the review rubric): it applies whatever
  policy it is given and holds none.
- An injectable strategy port (a named `ToolContext.services` port) where a caller needs to supply
  intelligence. The reference strategies stay conservative and neutral.
- Documentation, executable examples, and tests, including failure and compatibility tests.

Out of scope here:
- Provider calls, credentials, OAuth, scheduling, workflow state, rendering internals and any effect.
- Anything opinionated: house scorers, word lists, thresholds, personas, profiles and publication
  names. They belong to the runner that hosts this library. `tests/test_architecture.py` guards the
  boundary.
- A second invoke path or runner. There is deliberately no invoke command.

## Owner-only areas
The requester still writes the proposal and the tests; the maintainer decides who writes the code.

| Area | Paths | Why |
|---|---|---|
| Release and publishing | version bumps, tags, `.github/workflows/publish.yml`, `.github/workflows/docs.yml`, the `pypi` and `testpypi` environments | A release goes through the release authority, never from a working branch (see [docs/release-readiness.md](docs/release-readiness.md)). The documentation site publishes when `main` changes. |
| Credentials, signing and auth | none held here | This library holds no credentials. Nothing here may add one. |
| The Zeocore pin and the Runtime host surface | `pyproject.toml`, `uv.lock`, `src/zeo_creator/provider.py` | `zeocore[runtime-host]==X` and `runtime-provider`'s canonical bytes. Runtime binds the provider inventory, so a change is qualified against the host protocol first ([ADR 0003](docs/adr/0003-bounded-zeocore-compatibility.md); the pin is exact). |
| Released contracts | `reference/schemas`, `src/zeo_creator/schemas` | The schemas and digests of a released tag are frozen. A change is a new version, and the maintainer rules on it. |
| The architecture boundary | `tests/test_architecture.py` | The secret and provider rules. |
| Anything that adds a dependency or a tool | `pyproject.toml`, `package.json`, the gate | See "How to build". |

## How to build
- **Fork and branch.** Fork `matorclawson/zeocreator` and name the branch
  `<your-seat>/<topic>-<yyyymmdd>`, where `<your-seat>` is the authoring seat's zmsg name (for example
  `zeo-rt/...` or `zeroemployee/...`). The lane reads the seat from the text before the first `/`, so
  a project name there is refused. Name the requesting seat's `sow:` in the PR body. Until the A1
  seat-list install, only the owner seat's PRs are admitted. Never push to the golden repository, and
  never force-push; update a branch with a merge commit.
- **Set up.** `make setup` installs the locked environment.
- **Heavy work runs on ZeoWork, not the repository volume.** Either clone and work there, or set these
  before you run `make`: `TMPDIR` for temporary files, `UV_PROJECT_ENVIRONMENT` for the virtual
  environment, `MYPY_CACHE_DIR` and `RUFF_CACHE_DIR` for the tool caches, and
  `PYTEST_ADDOPTS="-o cache_dir=<dir>"` for pytest's. Builds still land in `dist/` and `site/` in the
  checkout; `git clean -fdX dist site` removes them.
- **The gate is `make verify`.** It runs the release-identity check, the format check, lint, strict
  type-check, the test suite, regeneration and a byte-for-byte check of the reference artifacts, a
  strict docs build, the digest vectors, and builds and installs the wheel to run the conformance tests.
  It takes about 4 minutes. Run it once on the merge result before you open the PR, not in a loop.
- **Tests.** Every change adds a failure-path test as well as a passing one, and a compatibility test
  if it touches a contract. Examples and tests never contact a live provider. This repository does not
  use mutation testing.
- **Contracts and generated files.** After a contract or capability change run `make reference`, and
  commit what it regenerates (`reference/`, `src/zeo_creator/schemas`, `src/zeo_creator/examples`,
  `src/zeo_creator/reference_artifacts`). The gate fails if they differ.
- **Docs and changelog.** Update the relevant guide, and add a line under `## Unreleased` in
  `CHANGELOG.md`. State plainly if the change is breaking.
- **Every dependency, new tool or pin goes through the Architect.** Never ask the operator. Name the
  dependency, the version and the source in a zmsg to the Architect, through the maintainer. A
  dependency change is a sensitive change and takes the sensitive review route.
- **Publication core (JavaScript).** `packages/publication-core/` contains pure publication metadata
  fundamentals, separate from the Python package. Its own future tag namespace is owner-issued and
  must never use the Python `v*.*.*` tags; no JS publishing runs here. Its tests run as
  `node --test` inside `make verify`. The Architect accepted Node.js as a gate tool on these conditions:
  Node 24 LTS, pinned by `engines` in `packages/publication-core/package.json` and a `.node-version`,
  and `make verify` refuses a different major. The package has zero npm packages; any package, even
  dev-only, goes to the Architect first with name, version, publisher, downloads and age. It is not part
  of the Python wheel or sdist, and is never published from here.
- **CLI conventions** (Zeocore's `cli_protocol` 1). Every command prints exactly one JSON line on
  stdout, carrying `ok` and `"schema": "zeocreator.<thing>/v1"`. Exit codes are 0 done, 1 internal
  (no detail), 2 invalid input, 20 held or refused. Nothing prompts, and an error never echoes input on
  stdout. `--json` is accepted and changes nothing. `runtime-provider` is the one named exception: it
  prints canonical bytes without `ok`, which Runtime reads, so it is owner-only (above). A new command
  is added to the `help --json` catalogue with its output schema id.

## How to submit
- **One ready PR at a time**, from your fork to `main`. While it waits, keep building on a branch stacked on
  it in your fork, and open the next PR when the one below merges.
- **Fetch `main` and re-run the gate on the merge result** before you ask for review. Other pull
  requests merge under you, and two correct changes can conflict.
- **PR body.** Name the head as `fork:branch` at the exact commit, and the base commit. Then:
  what changed and why, anything breaking, the proposal it answers, and what is deliberately not
  included.
- **Evidence.** The first line of the `make verify` log is `head: <full sha>` (from `git rev-parse HEAD`),
  so it can't be taken for another commit's. Then the exit code and the test counts, and the SHA-256 of
  the diff against the base commit (`git diff <base-sha>...HEAD | shasum -a 256`). This repository
  does not use a bundle or a `SHA256SUMS` file.
- **Route:** owner, then council, then zeomerger. Until zeomerger is live for this repository, the
  Architect sequences the merge. **The operator never merges, and is never asked.** Do not merge or tag
  your own work.

## Response times
- A proposal is answered within **4 hours**.
- A pull request is reviewed within **1 working day**, and a re-review of a fix within **4 hours**.
- Longer only with a stated reason. A refusal always names the rule it rests on, and a request for
  changes lists each finding by file and line, so a contributor can fix them in one pass.

## Escalation
A missed time goes to the Architect by zmsg.
