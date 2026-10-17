# Releases and readiness

## Version 0.6.0

This release requires `zeocore[runtime-host]==0.18.0` and gives the CLI Zeocore's `cli_protocol` 1.
The distribution remains `zeocreator`, import `zeo_creator` and CLI `zeo-creator`, on Python 3.14+.
The previous [0.5.4](releases/0.5.4.md) and [0.5.3](releases/0.5.3.md) release notes remain
available as historical evidence.

Install with `python -m pip install "zeocreator==0.6.0"` in a Python 3.14+
environment. Follow the [installation guide](getting-started/installation.md)
for a complete isolated setup and migration from the older Git-only distribution.

## What the release verifies

The package exposes 29 capabilities, including nine input-only email v4 capabilities.
Verification covers formatting, Ruff, strict typing, tests, deterministic schema,
corpus and example exports, strict documentation, JavaScript digests, wheel and
sdist metadata, and installed-wheel behavior outside the checkout. All eight
examples are installed; email programs exercise three isolated publications,
eight programs and 104 simulated proposals. The portable receipt corpus has 135 cases.

The source gate runs 355 tests. Another 34 conformance tests run outside the
checkout against the installed Core host and Creator wheel, including real
planner execution, artifact acceptance and refusal paths through a labelled
IPC test peer. These establish Creator/Core behavior, not deployed Runtime acceptance.

The accepted schema and corpus bytes are unchanged by packaging this release.
Package, capability and schema versions remain independent. Historical email
v1/v2/v3 schemas are archived; current preparation uses v4. An early 0.x release
does not promise 1.x API stability.

## Publishing workflow

`.github/workflows/publish.yml` follows
[Zeocore's release workflow](https://github.com/zeroemployeeorg/zeocore/blob/e630cc5c785f7e527bd597bde6d0949f4a7cc9a9/.github/workflows/publish.yml):
verify first, build and retain one wheel/sdist pair, publish with OIDC, test the
exact uploaded version on the minimum Python version, and create the GitHub
Release from `RELEASE_NOTES.md`. Creator also checks tag/metadata/notes agreement
before upload and waits for index smoke tests before announcing the release.

Publishing requires a trusted publisher for project `zeocreator` with owner
`zeroemployeeorg`, repository `zeocreator`, workflow filename `publish.yml` and
environment `pypi` (TestPyPI: environment `testpypi`). Each publishing job runs in
that GitHub environment, so an upload waits for the environment's required
approval. No PyPI API token is stored. See
[PyPI trusted publishing](https://docs.pypi.org/trusted-publishers/using-a-publisher/).

The repository moved from `profrodai/zeocreator` to `zeroemployeeorg/zeocreator`
after 0.5.4 was published. The publisher recorded for 0.5.3 and 0.5.4 named owner
`profrodai`. Whether PyPI and TestPyPI now match the required configuration has
not been verified since the move. Treat it as a possible release blocker until an
account administrator confirms it; do not publish to find out.

For each authorized release:

1. Update `pyproject.toml`, `uv.lock`, `CHANGELOG.md`, `RELEASE_NOTES.md`, examples
   and current guides. Keep historical schemas and artifacts intact.
2. Run `make reference`, stage intended generated resources, then run
   `make verify`, `make doctor` and all installed-wheel examples.
3. Merge the verified candidate through a ready PR after hosted checks pass.
4. Tag that main commit as `vX.Y.Z`, exactly matching the package version, and
   push the tag. The publish workflow runs the gates again before PyPI upload.
5. Verify the index's exact version, artifact hashes, installed CLI/examples,
   documentation site and GitHub Release. Never move a published tag or overwrite
   an uploaded version; corrections require a new release.

Manual dispatch supports `testpypi`, `pypi` or `both`, like Zeocore. Production
publication requires a matching version-tag ref even when dispatched manually.
TestPyPI requires a separately configured publisher; no TestPyPI binding or upload
is assumed. Its smoke test downloads the exact staged wheel and resolves other
dependencies from PyPI, avoiding mixed-index dependency resolution.

## Production integration remains separate

Creator designs and evaluates email programs. Zeocore owns public provider
contracts/lowering; ZEOconnect owns execution and credential custody; Runtime owns
authority, schedules and durable reconciliation. Newsroom owns persisted observations.
The released dependency is Zeocore 0.18.0. Creator exposes inventory and request
preparation for its shared host. Runtime still owns Go supervision, durable
operation recovery, artifact retrieval and managed-agent acceptance. See the
[Runtime host guide](guides/runtime-host.md) for the exact boundary.
Publication does not establish authenticated email-provider interoperability.

Hosts must pass the pinned 135-case v2 corpus with their own validators, authenticate
issuers and account/effect authority, verify current remote state, and qualify
real HubSpot Marketing/Kit behavior. The fake hosts are not production journals
or providers. Unsupported sequence semantics must refuse; ambiguous effects must
reconcile before retry. No live provider effect is authorized by releasing to PyPI.

See [email marketing](guides/email-marketing.md) and
[receipt conformance](guides/email-receipt-conformance.md).
