# Contributing to ZEO Creator

A contributors charter, written for agents first. The seat that needs a change proposes it, agrees the
shape with the maintainer, builds it on its own fork, and opens a pull request for review. The
maintainer guards the product's shape and the gate. Start with [AGENTS.md](AGENTS.md); this file is
the rest of the rules. The architecture rules and the steps for changing a contract are in
[docs/contributing.md](docs/contributing.md) and are not repeated here.

## How to propose
Open an issue in this repository, or send the maintainer a short note, **before you build**. Say:

- **Need:** what you cannot do today, in one or two sentences.
- **Design sketch:** the capability, contract or port you would add, its inputs and outputs, and which
  existing code it sits beside.
- **Who else gains:** another seat or product that would use it. A change only one caller needs usually
  belongs in that caller's runner, not here.
- **Risks:** what it could break, which released contract it touches, and whether it adds a dependency.

The maintainer answers within **4 hours** when the seat is running: yes, no, or "change the shape
like this". Build after that answer, not before. A change that touches an owner-only area (below) still
starts with a proposal and the tests; the maintainer decides who writes the code.

## What is welcome, and the shape the product keeps
ZEO Creator is a library of **pure capabilities and the contracts around them**. It never calls a
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

- **Release and publishing:** version bumps, tags, `.github/workflows/publish.yml` and the publishing
  environments. A release goes through the project's release process, never from a working branch.
- **The Zeocore pin and the Runtime host surface:** `zeocore[runtime-host]==X` and `runtime-provider`'s
  canonical bytes. Runtime binds the provider inventory, so a change here is qualified against the host
  protocol first (ADR 0003).
- **Released contracts:** the schemas and digests of a released tag are frozen. A change is a new
  version, and the maintainer rules on it.
- **The architecture boundary:** `tests/test_architecture.py` and the secret and provider rules.
- **Anything that adds a dependency** (see below).

## How to build
- **Fork and branch.** Work on your own fork, on a branch named `<your-seat>/<topic>-<date>`. Never
  push to this repository, and never force-push; update a branch with a merge commit.
- **Set up.** `make setup` installs the locked environment.
- **The gate is `make verify`.** It runs lint, strict type-check, the test suite, regeneration and a
  byte-for-byte check of the reference artifacts, a strict docs build, the digest vectors, and builds
  and installs the wheel to run the conformance tests. It takes about 4 minutes. Run it once on the
  merge result before you open the PR, not in a loop.
- **Heavy work runs on the scratch volume.** Run `make verify` with `TMPDIR` pointing at the
  organisation's scratch volume (ZeoWork), never the repository volume. Builds land in `dist/` and
  `site/`; `git clean -fdX dist site` removes them.
- **Tests.** Every change adds a failure-path test as well as a passing one, and a compatibility test
  if it touches a contract. Examples and tests never contact a live provider. This repository does not
  use mutation testing.
- **Contracts and generated files.** After a contract or capability change run `make reference`, and
  commit what it regenerates (`reference/`, `src/zeo_creator/schemas`, `src/zeo_creator/reference_artifacts`).
  The gate fails if they differ.
- **Docs and changelog.** Update the relevant guide, and add a line under `## Unreleased` in
  `CHANGELOG.md`. State plainly if the change is breaking.
- **No new dependency without the operator's OK.** Ask the maintainer, who asks the operator. A
  dependency change is a sensitive change and takes two review voices.
- **CLI conventions** (Zeocore's `cli_protocol` 1). Every command prints exactly one JSON line on
  stdout, carrying `ok` and `"schema": "zeocreator.<thing>/v1"`. Exit codes are 0 done, 1 internal
  (no detail), 2 invalid input, 20 held or refused. Nothing prompts, and an error never echoes input on
  stdout. A new command is added to the `help --json` catalogue with its output schema id.

## How to submit
- **One PR at a time**, from your fork to `main`. While it waits, keep building on a branch stacked on
  it in your fork, and open the next PR when the one below merges.
- **Fetch `main` and re-run the gate on the merge result** before you ask for review. Other pull
  requests merge under you, and two correct changes can conflict.
- **PR body.** Name the head as `fork:branch` at the exact commit, and the base commit. Then:
  what changed and why, anything breaking, the proposal it answers, and what is deliberately not
  included.
- **Evidence.** The `make verify` result with the head first (exit code and the test counts), and the
  SHA-256 of the diff against the base (`git diff main...HEAD | shasum -a 256`).
- **Review route:** the maintainer, then the council, then the merger. A sensitive change (a
  dependency, a workflow, a released contract) needs two voices. Do not merge or tag your own work.

## Response times the maintainer commits to
- A proposal is answered within **4 hours**.
- A pull request gets its first review within **1 working day**, and a re-review of a fix within
  4 hours.
- A refusal always names the rule it rests on, and a request for changes lists each finding by file
  and line, so a contributor can fix them in one pass.
