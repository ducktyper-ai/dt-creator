# Contributing

ZEO Creator is strict about boundaries because a convenient shortcut in creator
code can become an authority or credential leak in production.

## Set up

```console
git clone https://github.com/zeroemployeeorg/dt-creator.git
cd zeocreator
uv sync --frozen
make verify
```

## Useful commands

| Command | Purpose |
|---|---|
| `make verify` | Lint, strict type-check, test, regenerate references, and build docs |
| `make examples` | Run every public example |
| `make docs-serve` | Serve the documentation with live reload |
| `make reference` | Regenerate JSON schemas and neutral reference artifacts |
| `make doctor` | Check Python, Zeocore, manifests, and projections |

## Architecture rules

- Capabilities, contracts, and services must not import provider SDKs or runtime
  products.
- Credentials must never enter a request, response, artifact, log, exception,
  manifest, proposal, or receipt.
- Read dependencies arrive through named `ToolContext.services` ports.
- Distribution construction performs no external write.
- Cross-publication identity mismatch is a blocking failure.
- Durable changes require new revisions and digests.
- Do not add a monolithic daily runner or scheduler.

## Change a contract

1. Update the Pydantic contract and capability models.
2. Update examples and error declarations.
3. Add failure-path and compatibility tests.
4. Run `make reference` to regenerate schemas.
5. Update the relevant guide and API reference.
6. Run `make verify` from a clean environment.

## Documentation standard

Examples must be executable and credential-free. Prefer one complete copy-paste
path before explaining every option. Keep conceptual rationale separate from
task-oriented how-to guides and generated API reference.

## Safety

Tests and examples must never contact a live provider or require a reusable
credential. PyPI publication and provider effects require separate operator
approval.
