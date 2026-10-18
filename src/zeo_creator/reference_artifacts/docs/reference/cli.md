# CLI reference

The CLI is intentionally small. It supports discovery and diagnostics, not
production workflow orchestration.

## `zeo-creator capabilities`

List the canonical capability manifests, as `{"ok": true, "capabilities": [...]}`:

```console
zeo-creator capabilities
```

Emit OpenAI-compatible function projections, as `{"ok": true, "tools": [...]}`:

```console
zeo-creator capabilities --projection openai
```

## `zeo-creator runtime-provider`

Added in 0.5.4. Emit the complete installed inventory as
one canonical JSON document for trusted Runtime provisioning. It is the one exception
to the [operating protocol](#operating-protocol): its line is the inventory itself,
without `ok`, until Runtime confirms a reader for the JSON-lines form. Then it changes
in one release, to `{"ok": true, "provider": <the same inventory>}`.

```console
zeo-creator runtime-provider
```

This performs no invocation or admission. Runtime supplies the verified
`environment_digest` and `generation` to form Core's `ProviderBinding`, then
uses the [shared host](../guides/runtime-host.md) for scoped discovery and calls.

## `zeo-creator doctor`

Check the interpreter, exact Zeocore version, manifest discovery, and projection
compatibility:

```console
zeo-creator doctor
```

The result carries `ok` and each check. A failed check exits 20.

## Contract schemas

List the stable contract catalog, as `{"ok": true, "contracts": [...]}`:

```console
zeo-creator contracts list
```

Export the schemas bundled in the installed wheel:

```console
zeo-creator contracts export --output=./schemas
```

Print one named contract version, as `{"ok": true, "json_schema": {...}}`:

```console
zeo-creator contract-schema --name=content-brief --version=1
```

## `zeo-creator --version`

```console
zeo-creator --version
```

The result is `{"ok": true, "zeocreator": "X.Y.Z", "cli_protocol": "1"}`.

## `zeo-creator help --json`

The machine catalogue. An agent learns the CLI from it rather than from the
source: every command, with its options (flags, type, required, default,
choices), its output schema ids, the exit codes and the error schema.

```console
zeo-creator help --json
```

## Operating protocol

Other seats and tools operate the CLI through this fixed contract:

- `zeo-creator help --json` is the machine catalogue. `--help` on the root and on
  every command prints human-readable text, the only output that isn't JSON.
- **Every result names its schema:** `"schema": "zeocreator.<thing>/v1"`, for
  example `zeocreator.doctor/v1`, `zeocreator.contracts/v1` or
  `zeocreator.error/v1`. The catalogue lists each command's schema ids.
- **stdout is JSON lines and nothing else.** No command emits events, so each
  prints exactly one line: the result, which carries `ok`. Diagnostics, such as
  usage text, go to stderr. `--json` is still accepted and changes nothing.
- **Errors say what to do, and never echo input on stdout.** An invalid request
  answers `{"ok": false, "outcome": "invalid_request", "reason": ..., "next": ...}`.
  For a command-line usage error the reason is one of seven fixed phrases (`unknown
  command`, `missing command`, `unknown option`, `missing required option`, `invalid
  option value`, `unknown contract`, and `invalid command line` for anything else), also
  listed by `help --json` as `usage_error_reasons`. A command that validates its own input
  (`lint-thread`) answers the same shape with its own fixed reason, for example `draft is
  not valid JSON`; those reasons are not in that list. `next` is the command to run:
  `zeo-creator help --json`, or `zeo-creator contracts list` for an unknown
  contract. Neither names what was sent. An internal error carries only a `next`
  step. The usage text on stderr can name the unknown option, because stderr carries
  diagnostics for a person.
- **`doctor` names the fix:** each failing check appears in `next` with the exact
  command that fixes it, or who must act. A healthy install has `"next": []`.
- **The one exception is `runtime-provider`,** whose canonical bytes Runtime
  reads. It ends when Runtime confirms a reader for the JSON-lines form.
- Exit codes follow Zeocore's `cli_protocol` 1, so they mean the same in every
  ZEO tool:

| Code | Meaning |
|---|---|
| `0` | Done |
| `1` | Internal error: stdout is `{"ok": false, "outcome": "internal", "schema": "zeocreator.error/v1"}`, with no detail |
| `2` | Invalid input or command: an unknown command, option or contract |
| `20` | Refused: a check failed (`doctor` reports `"ok": false`) |

Codes 10 to 13 concern remote operations, which this CLI never performs.

## Install, upgrade and rollback

Install a published release as a tool, never a checkout, then check it:

```console
make install VERSION=0.6.0
```

This runs `uv tool install --force "zeocreator==0.6.0"` and then
`zeo-creator doctor --json`. To upgrade, or to roll back, run the same command
with the version you want.

## What is intentionally absent

There is no daily-run, schedule, approve, publish, OAuth, credential, or daemon
command. Those operations belong to Sovereign Agent, a ZEO runtime, or managed
connection infrastructure.
