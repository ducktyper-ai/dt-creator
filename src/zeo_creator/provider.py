"""Offline provider preparation for Zeocore's Runtime-supervised host.

These helpers describe installed code and normalize business input. They do not
create a launch context, grant, Runtime session, or permission to invoke it.
"""

import platform
from dataclasses import dataclass
from importlib.metadata import version
from typing import Any

from zeo_core.adapters.runtime_host.canonical import (
    MAX_BYTES,
    InvalidRequestError,
    ProtocolError,
    canonical_bytes,
    digest,
    manifest_inventory,
    parse_json,
)
from zeo_core.adapters.runtime_host.catalogue import validate_inventory
from zeo_core.adapters.runtime_host.host import prepare_request
from zeo_core.contracts.runtime import InvocationRequest, ProviderBinding

from zeo_creator.registry import capability_registry

PROVIDER_FACTORY = "zeo_creator.registry:capability_registry"
CORE_VERSION = "0.18.0"


def provider_inventory() -> dict[str, Any]:
    """Describe this installation; Runtime must independently verify and admit it.

    The factory always contributes the complete catalogue. Runtime filters
    discovery and fills admitted_capabilities rather than trimming this inventory.
    """
    if version("zeocore") != CORE_VERSION:
        raise ProtocolError("Creator requires its exact supported Zeocore release")
    manifests = manifest_inventory(capability_registry().manifests())
    inventory = {
        "protocol_version": 1,
        "distribution": "zeocreator",
        "version": version("zeocreator"),
        "python_version": platform.python_version(),
        "factory": PROVIDER_FACTORY,
        "manifests": manifests,
        "manifest_digest": digest(manifests),
    }
    if len(canonical_bytes(inventory)) > MAX_BYTES:
        raise ProtocolError("Creator inventory exceeds the host message limit")
    return inventory


def provider_binding(*, environment_digest: str, generation: int) -> ProviderBinding:
    """Prepare Core's binding using values supplied by the trusted launcher.

    environment_digest must identify the environment verified by Runtime. This
    function neither measures that environment nor authenticates this document.
    """
    data = provider_inventory()
    data.update(environment_digest=environment_digest, generation=generation)
    raw = canonical_bytes(data)
    if len(raw) > MAX_BYTES:
        raise ProtocolError("Creator binding exceeds the host message limit")
    binding = ProviderBinding.model_validate_json(raw)
    validate_inventory(binding)
    return binding


@dataclass(frozen=True)
class PreparedInvocation:
    """Validated/default-materialized request and its Core authorization digest."""

    request: InvocationRequest
    request_digest: str


def prepare_invocation(raw: bytes) -> PreparedInvocation:
    """Normalize strict wire JSON before Runtime binds its exact request digest.

    JSON duplicate keys, oversize input, unknown IDs, invalid schemas and invalid
    business input refuse. This does not execute the selected capability.
    """
    parse_json(raw)
    try:
        request = InvocationRequest.model_validate_json(raw)
        registry = capability_registry()
        capability = next(
            (
                c
                for c in registry.list_all()
                if c.definition.id.canonical() == request.capability_id
            ),
            None,
        )
        if capability is None:
            raise InvalidRequestError("unknown exact Creator capability ID")
        validated = prepare_request(capability, request)
        normalized = InvocationRequest.model_validate_json(
            canonical_bytes(
                {
                    "protocol_version": 1,
                    "capability_id": request.capability_id,
                    "arguments": validated.model_dump(mode="json"),
                }
            )
        )
    except ValueError as exc:
        raise InvalidRequestError("invalid Creator invocation") from exc
    if len(canonical_bytes(normalized.model_dump(mode="json"))) > MAX_BYTES:
        raise InvalidRequestError("normalized Creator request exceeds the host message limit")
    return PreparedInvocation(
        request=normalized,
        request_digest=digest(
            {"capability_id": normalized.capability_id, "arguments": normalized.arguments}
        ),
    )
