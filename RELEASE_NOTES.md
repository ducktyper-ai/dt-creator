# zeocreator 0.6.0

**The CLI now follows Zeocore's `cli_protocol` 1, and Creator requires Zeocore 0.18.0.**
This is a breaking change for anyone who parses the CLI's output or exit codes: read the
"CLI changes" section before upgrading. The library API, the 29 capability identities and the
released contract schemas are unchanged.

## Install or upgrade

Use Python 3.14 or newer in a fresh environment:

```console
uv venv --python 3.14 .venv
uv pip install --python .venv/bin/python "zeocreator==0.6.0"
.venv/bin/zeo-creator doctor
.venv/bin/zeo-creator help --json
```

With pip, install `zeocreator==0.6.0` in a Python 3.14+ virtual environment. Zeocore 0.18.0 and its
host dependencies install automatically. The distribution remains `zeocreator`, the import
`zeo_creator`, and the CLI `zeo-creator`. Retain a deployment lockfile and verify wheel provenance.
`make install VERSION=0.6.0` installs this release as a tool and runs `doctor`.

## CLI changes (breaking)

- Every command except `runtime-provider` prints exactly one JSON line on stdout: the result, which
  carries `ok` and `"schema": "zeocreator.<thing>/v1"`. The rich tables are gone, and `--json` is
  accepted and changes nothing.
- Lists are wrapped: `capabilities` answers `{"capabilities": [...]}` (or `"tools"` with
  `--projection openai`), `contracts list` answers `"contracts"`, and `contract-schema` answers the
  JSON Schema under `json_schema`. `--version` answers `{"ok": true, "zeocreator": "0.6.0", "cli_protocol": "1"}`.
- Exit codes follow Zeocore's `cli_protocol` 1: 0 done, 1 internal error (no detail), 2 invalid
  input, 20 held or refused. **A failed `doctor` check now exits 20, not 1.**
- A usage error prints its usage on stderr and an `invalid_request` result on stdout, exit 2, and
  never echoes what you typed on stdout. Running with no command is a usage error.
- `zeo-creator help --json` is a machine catalogue of every command, option, exit code and output
  schema id.
- `runtime-provider` keeps its canonical bytes, without `ok`, until Runtime confirms a reader for the
  JSON-lines form. Then it changes in one release.
- Shell-completion options are removed.

## What else changed

- **Requires `zeocore[runtime-host]==0.18.0`** (was 0.11.0). Zeocore 0.15.0 made every runtime-host
  name Creator uses public, and the runtime-host-v1 protocol files are byte-identical from 0.11.0
  through 0.18.0. `doctor` reports the check as `zeocore_0_18_0`.
- **Fix:** the reference story-revision strategy now chains same-topic signals in one batch into
  successive revisions (1, 2, ...) with `previous_revision_ref` set, instead of several unrelated
  revision 1s of one story. Reference artifacts and contract digests are unchanged.
- **Fix:** `extract_editorial_signals`, `update_story_revisions` and `build_story_dossier` now refuse an
  injected strategy's output that cites a signal, source, revision, story or lineage reference that is
  not an input of the same call, using the error codes they already declare.
- **Add** `zeo_creator.rendering.render_email_body`, a pure renderer from structured blocks to an
  escaped, accessible HTML fragment for a template slot, with its plain-text twin and digests that
  match `EmailDeliveryMaterial`.
- **Email links** now refuse a backslash, which browsers read as a path separator that URL parsers do
  not, so a link cannot show one host and open another.
- **Docs and tests:** the shared JCS test vectors and wire rule 7 (a digest covers the fully
  materialized contract), and ADR 0003 on bounded Zeocore compatibility.
- **Release process:** publishing runs in the GitHub environments `pypi` and `testpypi`. The direct
  `rich` dependency is dropped (Typer still installs it).

## Compatibility

Released schemas and the 29 capability identities are unchanged. This remains an early 0.x API: pin
the package and contract versions. Release publication does not establish live HubSpot or Kit
interoperability; execution and account qualification belong to the host.
