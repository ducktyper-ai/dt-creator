# Offline CANDIDATE artifacts

This developer tool prepares and checks a **CANDIDATE**, not an owner-issued artifact.
The source package remains private. There is no registry operation, lifecycle script,
package identity change, runtime change or additional dependency.

Use the admitted Node 24 installation and its bundled npm CLI. Run inside the applicable
offline execution controls; `--offline` and `--ignore-scripts` are application settings,
not an OS network sandbox. Heavy qualification runs use the supported ENG route.

```sh
node packages/publication-core/tools/candidate-distribution.mjs build \
  --repo /absolute/clean/checkout --source FULL_40_CHARACTER_HEAD \
  --out /absolute/new/scratch/candidate \
  --npm-cli /absolute/admitted/npm/bin/npm-cli.js
node packages/publication-core/tools/candidate-distribution.mjs verify \
  --repo /absolute/checkout --source FULL_40_CHARACTER_SOURCE \
  --archive /absolute/candidate/candidate.tgz \
  --index /absolute/candidate/candidate-index.json
```

The output directory must not exist and must be outside the source checkout. A successful
command prints one JSON object with `ok: true`, `candidate: true`, `label: "CANDIDATE"`;
a refusal prints a fixed body-free `candidate_refused` result and exits 20. The tool
uses isolated temporary HOME/config/cache and removes only its own scratch directory.
It neither downloads inputs nor silently repairs a candidate.

The build reads regular Git blobs at the exact clean HEAD. Selection derives from the
package's `files` plus npm's mandatory metadata. This version supports literal regular
file entries, not directory or glob selections. Actual npm pack member paths/sizes are
compared with a separately parsed tgz, and every member is checked against source blobs.
The closed versioned index binds source commit, package identity/private flag, sorted member
paths/sizes/SHA256 values and archive size/SHA256/SHA512 integrity. Verification requires an
independently supplied expected source commit and locally available Git objects; a
self-consistent index cannot authorize different source bytes. The index is not a signature or a canonical JSON serialization. Field order and whitespace may differ; verification checks the closed structure and exact member/source/archive bindings, not a canonical index-byte digest.

Source identities must name actual commit objects; a tree or annotated-tag object ID is refused. Source cleanliness compares the real index with that commit and inspects worktree bytes using disposable private Git metadata, without importing repository clean filters, fsmonitor or submodule configuration. Submodule trees are refused; assume-unchanged/skip-worktree index flags cannot hide changed files. Existing-directory and parent realpaths enforce physical source/output separation, including case aliases on case-insensitive filesystems.

The tool deliberately uses `/usr/bin/git` on supported POSIX hosts. That exact executable and its runtime must be part of the receiver-adopted closure; there is no PATH search or download fallback. Public CLI refusals retain the fixed body-free `candidate_refused`/exit20 contract; internal guards have named errors for focused assertions.

Archive parsing is bounded and supports regular USTAR members only. It refuses duplicate,
absolute, traversing, noncanonical, link, executable, extended-header, malformed, truncated
and unexpected members. Unsupported archive forms are refusals, not automatic rewrites.
JSON duplicate keys, including escaped aliases, and unknown schema fields also refuse.
Limits are 2 MiB compressed/index/member, 16 MiB decompressed and 64 archive members.
These application limits do not provide kernel process/memory/disk quotas or protect against
another actor mutating a shared filesystem. No private inputs belong in these artifacts.

Root LICENSE inclusion is **off by default**. The tool does not invent licensing policy.
Only after a separate owner policy decision, `--root-license-provenance FILE` can supply
the exact JSON object `{"sourcePath":"LICENSE","sourceCommit":"FULL_SHA","sha256":"FULL_SHA256"}`.
The named root regular Git blob must belong to the same source commit and match the digest;
its destination is recorded as `LICENSE`. The feature is not permission to adopt a license.
The synthetic test exercises this input with synthetic text; it does not adopt the repository's
root license for an actual candidate.

Tests use synthetic Git/package inputs, a fresh offline consumer and bundled npm with lifecycle
scripts disabled. They verify installation, import/API behavior and installed member hashes,
plus provenance, integrity, schema, tar and source/output guard refusals. Installation and
runtime import do **not** establish compiler/type soundness of the hand-authored declarations.
That remains an explicit gap. These checks do not establish integration with consuming sites.

Run the focused test file with the admitted Node, then run the repository's `make verify`
and `make doctor` once on the frozen source before review. Preserve exact source, commands,
exits and logs. One draft PR may queue behind the maintainer's existing ready PR; readiness
requires actual queue clearance. Compatibility receiving, independent review and canonical
receiving remain distinct from producing a candidate.

The focused test joins `make verify` through the publication-core test glob. The existing publication workflow also runs `make verify` and `make doctor`, so these child-process/offline-consumer tests participate in release validation. No workflow or release trigger is changed. A canonical private TMPDIR is used for fixtures, with an explicit aliased-temp positive/refusal control. Full gates and green CI must bind the actual final merged candidate; earlier frozen or synthetic-merge receipts do not qualify later bytes.
