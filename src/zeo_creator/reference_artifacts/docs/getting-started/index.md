# Getting started

You can adopt ZEO Creator incrementally. Start with a deterministic local
capability, then supply already-collected observations, and introduce a managed runtime
when you need recurring commitments and authorized provider effects.

## Choose your path

=== "I am evaluating the package"

    1. [Install from PyPI](installation.md).
    2. [Invoke your first capability](first-capability.md).
    3. Run `python -m zeo_creator.examples.email_marketing` in your environment.

=== "I am building a creator workflow"

    1. Read the [content portfolio tutorial](../tutorials/content-portfolio.md).
    2. Collect [evidence outside Creator](../guides/connectors.md).
    3. Hand accepted briefs to a [production adapter](../guides/production-adapters.md).

=== "I am integrating a managed runtime"

    1. Learn the [architecture boundary](../concepts/architecture.md).
    2. Follow the [runner integration guide](../guides/runner-integration.md).
    3. Keep effect authorization outside ZEO Creator.

## What you need

- Python 3.14 or newer
- `uv` or another Python package installer
- Zeocore 0.28.0 with the `runtime-host` extra, installed automatically and pinned exactly
- No credentials for the quickstart or examples

When you introduce real sources, your runner—not the capability request—must own
connections and credentials.
