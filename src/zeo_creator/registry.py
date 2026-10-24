"""Explicit capability discovery catalog for any controlling runner."""

from zeo_core.adapters.llm_tools import OpenAIFunctionTool, project_openai_tool
from zeo_core.contracts import CapabilityManifest
from zeo_core.tools import BoundCapability, CapabilityRegistry, bound_capability_of

from zeo_creator.capabilities import (
    assess_email_program,
    assess_performance,
    build_story_dossier,
    compose_commentary,
    compose_email_message,
    compose_news_article,
    compose_newsletter_issue,
    create_content_brief,
    evaluate_rubric,
    extract_editorial_signals,
    finalize_email_campaign,
    identify_engagement_opportunities,
    plan_content_portfolio,
    plan_edition,
    plan_editorial_agenda,
    plan_email_campaign,
    plan_email_message,
    plan_email_sequence,
    plan_newsletter_issue,
    prepare_correction,
    prepare_distribution,
    prepare_email_delivery,
    propose_email_operation,
    research_synthesis,
    review_commentary,
    review_email_message,
    review_news_article,
    review_newsletter_issue,
    update_story_revisions,
    validate_delivery,
)

CAPABILITIES: tuple[BoundCapability, ...] = tuple(
    bound_capability_of(item)
    for item in (
        research_synthesis,
        extract_editorial_signals,
        update_story_revisions,
        build_story_dossier,
        plan_editorial_agenda,
        plan_edition,
        identify_engagement_opportunities,
        compose_commentary,
        review_commentary,
        plan_newsletter_issue,
        compose_newsletter_issue,
        review_newsletter_issue,
        compose_news_article,
        review_news_article,
        prepare_correction,
        plan_content_portfolio,
        create_content_brief,
        validate_delivery,
        evaluate_rubric,
        prepare_distribution,
        assess_performance,
        plan_email_campaign,
        plan_email_sequence,
        plan_email_message,
        compose_email_message,
        review_email_message,
        prepare_email_delivery,
        finalize_email_campaign,
        propose_email_operation,
        assess_email_program,
    )
)


def capability_registry() -> CapabilityRegistry:
    registry = CapabilityRegistry()
    for item in CAPABILITIES:
        registry.register(item)
    return registry


def capability_manifests() -> tuple[CapabilityManifest, ...]:
    return tuple(capability_registry().manifests())


def openai_tool_projections() -> tuple[OpenAIFunctionTool, ...]:
    projections: list[OpenAIFunctionTool] = []
    for manifest in capability_manifests():
        result = project_openai_tool(manifest)
        if not result.ok or result.tool is None:
            detail = result.incompatibility or "unknown incompatibility"
            raise ValueError(f"Cannot project {manifest.id.canonical()}: {detail}")
        projections.append(result.tool)
    return tuple(projections)


__all__ = [
    "CAPABILITIES",
    "capability_manifests",
    "capability_registry",
    "openai_tool_projections",
]
