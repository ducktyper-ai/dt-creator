# zeocreator 0.5.4

**Creator can now be invoked through the shared Zeocore Runtime host.**
This release upgrades to `zeocore[runtime-host]==0.11.0`, adds provider provisioning
and normalized request preparation, and preserves all 29 capability identities.

## Install or upgrade

Use Python 3.14 or newer in a fresh environment:

```console
uv venv --python 3.14 .venv
uv pip install --python .venv/bin/python "zeocreator==0.5.4"
.venv/bin/zeo-creator doctor --json
.venv/bin/zeo-creator runtime-provider > creator-inventory.json
.venv/bin/python -m zeo_creator.examples.runtime_portfolio > creator-request.json
```

With pip, install `zeocreator==0.5.4` in a Python 3.14+ virtual environment.
Core 0.11.0 and its host dependencies install automatically. The distribution
remains `zeocreator`, the import `zeo_creator`, and the CLI `zeo-creator`.
Remove the earlier Git-only `zeo-creator` distribution before installing, or use
a fresh environment. Retain a deployment lockfile and verify wheel provenance.

## What changed

- Upgrade the exact Core dependency from 0.9.0 to 0.11.0 with the `runtime-host` extra.
- Add `zeo-creator runtime-provider` for the complete installed 29-manifest inventory,
  interpreter identity, factory and canonical manifest digest.
- Add `provider_inventory`, `provider_binding` and `prepare_invocation` helpers.
  Request preparation validates and normalizes input without invoking a handler.
- Use the existing `zeo_creator.registry:capability_registry` factory with Core's
  `zeo-capability` host; the first managed operation is `creator.plan_content_portfolio@1.0.0`.
- Package the offline `runtime_portfolio` request example and document exact
  provisioning, scope, admission, digest and artifact-publication bindings.
- Exercise real Core/Creator subprocess behavior and refusal paths in 34 installed
  conformance tests. The source suite has 355 tests; local and index smoke gates
  run all eight installed examples and the 135 portable email receipt cases.
- Update installation, CLI, Runtime, compatibility and release documentation.

## Compatibility and integration boundaries

All existing capability IDs, business schemas and email receipt corpus bytes are
preserved. Email preparation remains v4. This remains an early 0.x API; pin package
and contract versions independently. Core's exact dependency upgrade may require
updating the host application's lockfile.

Creator/Core conformance uses an explicitly labelled IPC test peer. Runtime still
owns real Go supervision, durable operation recovery, artifact retrieval and a
scoped managed-agent acceptance run. Publication does not claim that integration
is complete. The host requires Runtime acceptance of the result artifact before
reporting success; a process exit alone is not sufficient.

Twenty-seven supplied-input transformations need no injected service. The shared
host does not inject `creator.evidence_source` or `creator.metrics_source`, so
`research_synthesis` and `assess_performance` remain unavailable through it.
Existing direct Python integrations can continue supplying their documented ports.
Creator does not send mail, authorize effects, hold credentials or schedule jobs.
Live HubSpot/Kit interoperability remains separately qualified integration work.

[Documentation](https://zeroemployeeorg.github.io/zeocreator/) ·
[Installation](https://zeroemployeeorg.github.io/zeocreator/getting-started/installation/) ·
[Runtime host guide](https://zeroemployeeorg.github.io/zeocreator/guides/runtime-host/) ·
[Changelog](https://github.com/zeroemployeeorg/zeocreator/blob/v0.5.4/CHANGELOG.md) ·
[Previous release notes](https://zeroemployeeorg.github.io/zeocreator/releases/0.5.3/)
