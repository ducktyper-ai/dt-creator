"""Adoption documentation has stable entry points and complete navigation."""

from pathlib import Path


def test_readme_has_primary_adoption_paths() -> None:
    readme = Path("README.md").read_text()

    for heading in (
        "## Why ZEO Creator?",
        "## Install",
        "## First capability",
        "## Capability families",
        "## The authority boundary",
        "## Reference workflow",
        "## Development",
    ):
        assert heading in readme
    assert "https://github.com/zeroemployeeorg/dt-creator" in readme


def test_mkdocs_navigation_targets_exist() -> None:
    expected = {
        "index.md",
        "getting-started/index.md",
        "getting-started/installation.md",
        "getting-started/first-capability.md",
        "tutorials/content-portfolio.md",
        "guides/connectors.md",
        "guides/production-adapters.md",
        "guides/delivery-distribution.md",
        "guides/performance.md",
        "guides/runner-integration.md",
        "concepts/architecture.md",
        "concepts/contracts.md",
        "concepts/continuous-editorial-operations.md",
        "reference/capabilities.md",
        "reference/contracts.md",
        "reference/errors.md",
        "reference/cli.md",
        "contributing.md",
    }
    docs = Path("docs")

    assert all((docs / relative).is_file() for relative in expected)


def test_docs_do_not_teach_credential_transport_or_direct_publish() -> None:
    docs_text = "\n".join(path.read_text() for path in Path("docs").rglob("*.md"))

    assert "os.environ[" not in docs_text
    assert "api.twitter.com" not in docs_text
    assert "api.linkedin.com" not in docs_text


def test_public_material_describes_a_generic_producer_boundary() -> None:
    readme = Path("README.md").read_text()
    assert "producer-neutral" in readme
    assert "ContentBrief" in readme
    assert "ArtifactManifest" in readme
    assert "contracts export" in readme
