# Installation

Install `zeocreator==0.6.0` from PyPI with Python 3.14 or newer. Zeocore 0.18.0 is
installed automatically with its `runtime-host` extra; no credentials or accounts
are needed for the examples.

## Fresh environment

=== "uv"

    ```console
    uv venv --python 3.14 .venv
    uv pip install --python .venv/bin/python "zeocreator==0.6.0"
    .venv/bin/zeo-creator doctor --json
    .venv/bin/python -m zeo_creator.examples.create_content_brief
    .venv/bin/python -m zeo_creator.examples.email_marketing
    ```

=== "pip"

    ```console
    python3.14 -m venv .venv
    .venv/bin/python -m pip install "zeocreator==0.6.0"
    .venv/bin/zeo-creator doctor --json
    .venv/bin/python -m zeo_creator.examples.create_content_brief
    .venv/bin/python -m zeo_creator.examples.email_marketing
    ```

On Windows, use `.venv\Scripts\python.exe` and `.venv\Scripts\zeo-creator.exe`
in place of `.venv/bin/python` and `.venv/bin/zeo-creator`. In an existing uv
project, use `uv add "zeocreator==0.6.0"`, then prefix commands with `uv run`.

The PyPI distribution is **zeocreator**; the Python import is **zeo_creator**;
the executable is **zeo-creator**. The earlier Git-only distribution was named
`zeo-creator`. These are different installer project names despite sharing an
import path: use a fresh environment, or uninstall `zeo-creator` with your installer
before installing `zeocreator`. Do not install both distributions together.

## Verify and explore

After activating your environment (or using the explicit executable paths above):

```console
zeo-creator --version
zeo-creator doctor --json
zeo-creator capabilities
python -m zeo_creator.examples.complete_content_portfolio
python -m zeo_creator.reference.email_receipt_conformance
zeo-creator contracts export --output=./schemas
```

Version reports the JSON line `{"ok": true, "zeocreator": "0.6.0", "cli_protocol": "1"}`. Doctor reports `ok: true`, Python 3.14+,
Zeocore 0.18.0, 30 manifests and 30 projections. The receipt command verifies 135
portable cases; it does not authenticate provider receipts. The email example
prints eight programs and 104 simulated proposals with partial assessments.
All eight public examples are packaged under `zeo_creator.examples` and work
outside the source checkout. Their in-memory hosts never send an email.

## Work from the release source

```console
git clone --branch v0.6.0 https://github.com/zeroemployeeorg/dt-creator.git
cd zeocreator
uv sync --frozen
make doctor
make examples
make verify
```

The tag fixes the release source; `uv.lock` fixes its development environment.
Installed applications should retain their own lockfile as well.

!!! note "Why exactly Zeocore 0.18.0?"

    Creator pins the released shared Runtime host contract and its dependencies.
    Read the [architecture decision](../adr/0002-zeocore-runtime-host.md) and
    [Runtime host guide](../guides/runtime-host.md) for provider provisioning.
    Live HubSpot/Kit lowering still needs independent host integration and qualification.

Next, [invoke your first capability](first-capability.md) or follow the
[email marketing guide](../guides/email-marketing.md).
