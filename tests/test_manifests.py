"""Public capability-surface contract tests."""

import tomllib
from importlib.metadata import version
from pathlib import Path

from pydantic import BaseModel

from zeo_creator.registry import (
    CAPABILITIES,
    capability_manifests,
    capability_registry,
    openai_tool_projections,
)

EXPECTED_IDS = {
    "creator.finalize_email_campaign@4.0.0",
    "creator.propose_email_operation@4.0.0",
    "creator.plan_email_campaign@4.0.0",
    "creator.plan_email_sequence@4.0.0",
    "creator.plan_email_message@4.0.0",
    "creator.compose_email_message@4.0.0",
    "creator.review_email_message@4.0.0",
    "creator.prepare_email_delivery@4.0.0",
    "creator.assess_email_program@4.0.0",
    "creator.research_synthesis@1.0.0",
    "creator.extract_editorial_signals@1.0.0",
    "creator.update_story_revisions@1.0.0",
    "creator.build_story_dossier@1.0.0",
    "creator.plan_editorial_agenda@1.0.0",
    "creator.plan_edition@1.0.0",
    "creator.plan_content_portfolio@1.0.0",
    "creator.create_content_brief@1.0.0",
    "creator.validate_delivery@1.0.0",
    "creator.prepare_distribution@1.0.0",
    "creator.assess_performance@1.0.0",
    "creator.identify_engagement_opportunities@1.0.0",
    "creator.compose_commentary@1.0.0",
    "creator.review_commentary@1.0.0",
    "creator.plan_newsletter_issue@1.0.0",
    "creator.compose_newsletter_issue@1.0.0",
    "creator.review_newsletter_issue@1.0.0",
    "creator.compose_news_article@1.0.0",
    "creator.review_news_article@1.0.0",
    "creator.prepare_correction@1.0.0",
}


def test_declared_zeocore_version_is_exact() -> None:
    project = tomllib.loads(Path("pyproject.toml").read_text())["project"]
    assert project["requires-python"] == ">=3.14"
    assert "zeocore[runtime-host]==0.15.0" in project["dependencies"]
    assert version("zeocore") == "0.15.0"


def test_registry_exposes_the_stable_capability_surface() -> None:
    registry = capability_registry()
    assert {item.definition.canonical_id() for item in registry.list_all()} == EXPECTED_IDS
    assert {item.id.canonical() for item in capability_manifests()} == EXPECTED_IDS
    assert len(openai_tool_projections()) == len(EXPECTED_IDS)


def test_manifests_have_complete_contract_metadata_and_valid_examples() -> None:
    registry = capability_registry()
    for capability_id in EXPECTED_IDS:
        capability = registry.get(capability_id)
        manifest = next(
            item for item in capability_manifests() if item.id.canonical() == capability_id
        )
        assert manifest.request_schema
        assert manifest.response_schema
        assert manifest.effects.kinds
        assert manifest.examples
        assert manifest.error_codes
        assert manifest.projection_name
        for example in capability.definition.examples:
            parsed = capability.request_model.model_validate(example.request)
            assert isinstance(parsed, BaseModel)


def test_capability_tuple_matches_registry() -> None:
    assert {item.definition.canonical_id() for item in CAPABILITIES} == EXPECTED_IDS
