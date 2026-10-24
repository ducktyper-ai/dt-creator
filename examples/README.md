# Runnable examples

Every example is credential-free, deterministic, and exercised by CI.

| Example | Demonstrates |
|---|---|
| [`inspect_capabilities.py`](inspect_capabilities.py) | Manifest discovery, effects, and required services |
| [`create_content_brief.py`](create_content_brief.py) | Pure capability invocation and a typed producer-neutral brief |
| [`research_connector.py`](research_connector.py) | Runtime injection of a provider-neutral evidence source |
| [`validate_and_prepare.py`](validate_and_prepare.py) | Artifact validation and write-free distribution preparation |
| [`assess_performance.py`](assess_performance.py) | Legacy v1 injection of already-collected metrics |
| [`email_marketing.py`](email_marketing.py) | Three isolated publications, campaigns, sequences, fake lowering and input-only assessment |
| [`complete_content_portfolio.py`](complete_content_portfolio.py) | Validation of the neutral two-publication reference portfolio |

Install `zeocreator==0.5.3` on Python 3.14+, then run any example from any directory:

```console
python -m zeo_creator.examples.inspect_capabilities
python -m zeo_creator.examples.create_content_brief
python -m zeo_creator.examples.research_connector
python -m zeo_creator.examples.validate_and_prepare
python -m zeo_creator.examples.assess_performance
python -m zeo_creator.examples.complete_content_portfolio
python -m zeo_creator.examples.email_marketing
```

Use `uv run python` inside a uv-managed project. The portfolio reads packaged
fixtures, so a Git checkout is unnecessary. Email marketing prints eight programs,
104 simulated proposals and partial assessments; no message is sent.

From the repository root:

```console
uv sync --frozen
make examples
```

The examples deliberately use in-memory ports and synthetic observations. A
production runner acquires observations through Zeocore/ZEOconnect before Creator
invocation. Canonical email capabilities receive input artifacts without connectors.
