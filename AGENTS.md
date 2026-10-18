# ZEO Creator: start here (agents)

ZEO Creator is a public library of pure capabilities and the contracts around them: briefs,
artifact manifests, delivery reviews, distribution proposals and email. It is not a
runtime. It holds no credentials, calls no provider and runs no model. A runner supplies the
inputs and does any effect. The CLI only inspects it.

## The five commands that matter
Every command except `runtime-provider` prints one JSON line on stdout (the last line is the result and carries `ok` and
`schema`); `runtime-provider` prints canonical bytes without `ok`, and `--help` prints usage text. Exit codes: 0 done, 1 internal, 2 invalid input, 20 refused. Nothing prompts.

```console
zeo-creator help --json          # the whole CLI: commands, options, exit codes, output schemas
zeo-creator doctor               # checks the install; each failing check names its fix under "next"
zeo-creator capabilities         # the capability manifests (--projection openai for tool schemas)
zeo-creator contracts list       # the contract catalogue; contract-schema --name N --version 1 prints one
zeo-creator contracts export --output DIR   # all JSON Schemas, for any language
```

## The main job: invoke a capability, end to end
There is deliberately no invoke command (ADR 0002). Invoke through Python, which every example does:

```python
from zeo_core.tools import invoke_sync
from zeo_creator.capabilities.validate_delivery import ValidateDeliveryRequest
from zeo_creator.registry import capability_registry
from zeo_creator.runtime import make_context

registry = capability_registry()
capability = registry.get("creator.validate_delivery@1.0.0")
request = ValidateDeliveryRequest.model_validate(capability.definition.examples[0].request)
result = invoke_sync(capability, request, make_context(capability_name="validate_delivery"))
print(result.data)   # or result.human_message when it failed
```

Every capability ships a synthetic example request at `capability.definition.examples`. Packaged,
runnable examples: `python -m zeo_creator.examples.validate_and_prepare` (and the others in
`zeo_creator.examples`). A capability is pure: the same input gives the same output, and a refusal
returns a result with an error code, never a partial effect.

## Verify
`make verify` is the whole gate (lint, types, tests, reference artifacts, docs, wheel). Run
`make doctor` too. Both are slow (about 4 minutes), so run them once before a pull request, not in
a loop. `packages/publication-core/` is a private pure ESM package with zero npm dependencies; its Node 24 tests run in `make verify`, and it stays out of the Python distributions. To keep builds out of the checkout, set `DIST_DIR` and `SITE_DIR` (and `TMPDIR`) to a
scratch directory first.

## Never
- Add credentials, OAuth, provider SDKs, scheduling, workflow state, rendering or provider writes.
  `tests/test_architecture.py` forbids them in `src`, along with `os.environ` and provider hosts.
- Add anything opinionated: house scorers, lexicons, thresholds, personas, profiles or publication
  names. Those belong to the runner that hosts this library.
- Change a released contract in place. Schemas and digests of a released tag are frozen; a change
  is a new version.
- Release, tag or publish. Releases go through the project's release process, not from a working branch.

## How work lands
Work on a branch of your own fork and open one pull request at a time against `main`. Do not push
to the main repository, force-push, tag or release. Governed work follows the active statement of
work in the associated organization corpus.

To propose or contribute a change, read [CONTRIBUTING.md](CONTRIBUTING.md): how to propose, what
is welcome, the owner-only areas, how to build and submit, and the maintainer's response times.
