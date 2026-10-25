"""Creator/Core conformance with real installed subprocesses and a test IPC peer.

The peer is deliberately not ZEO Runtime. These tests do not establish Runtime
admission, persistence, isolation, restart recovery or managed-agent acceptance.
This file also runs outside the checkout against the built wheel.
"""

import copy
import hashlib
import json
import os
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import pytest
from zeo_core.adapters.runtime_host.canonical import (
    MAX_BYTES,
    canonical_bytes,
    digest,
    manifest_inventory,
)
from zeo_core.adapters.runtime_host.catalogue import CandidateCatalogue
from zeo_core.adapters.runtime_host.host import parse_result
from zeo_core.contracts.runtime import AttemptBinding, LaunchContext

from zeo_creator.capabilities.plan_content_portfolio import PlanContentPortfolioResponse
from zeo_creator.provider import prepare_invocation, provider_binding, provider_inventory
from zeo_creator.registry import capability_registry

PLANNER = "creator.plan_content_portfolio@1.0.0"


def invocation(capability_id=PLANNER):
    cap = capability_registry().get(capability_id)
    return {
        "protocol_version": 1,
        "capability_id": capability_id,
        "arguments": copy.deepcopy(cap.definition.examples[0].request),
    }


def binding():
    # Test fixture identity only: this does not measure a deployed environment.
    return provider_binding(environment_digest=digest("test-environment"), generation=1)


def test_full_inventory_and_all_examples_activate_without_registry_sharing():
    bound = binding()
    catalogue = CandidateCatalogue()
    active = catalogue.activate(bound, capability_registry)
    assert set(active.capabilities) == {
        c.definition.id.canonical() for c in capability_registry().list_all()
    }
    assert len(active.capabilities) == 30
    assert len(canonical_bytes(bound.model_dump(mode="json"))) < MAX_BYTES
    for cap in active.capabilities.values():
        for example in cap.definition.examples:
            prepare_invocation(
                canonical_bytes(
                    {
                        "protocol_version": 1,
                        "capability_id": cap.definition.id.canonical(),
                        "arguments": example.request,
                    }
                )
            )
    assert capability_registry() is not capability_registry()


def test_inventory_is_deterministic_across_hash_seeds_and_import_has_no_network():
    code = """
import sys
def guard(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "subprocess.Popen"}:
        raise AssertionError(event)
sys.addaudithook(guard)
from zeo_creator.provider import provider_inventory
from zeo_core.adapters.runtime_host.canonical import canonical_bytes
sys.stdout.buffer.write(canonical_bytes(provider_inventory()))
"""
    outputs = [
        subprocess.run(
            [sys.executable, "-c", code],
            env={**os.environ, "PYTHONHASHSEED": seed},
            check=True,
            capture_output=True,
            timeout=20,
        ).stdout
        for seed in ("1", "2", "3")
    ]
    assert outputs[0] == outputs[1] == outputs[2]
    inventory = json.loads(outputs[0])
    assert inventory["factory"] == "zeo_creator.registry:capability_registry"
    assert "environment_digest" not in inventory
    assert "generation" not in inventory


def test_defaults_are_bound_and_preparation_is_idempotent():
    raw = invocation()
    raw["arguments"].pop("revision", None)
    prepared = prepare_invocation(canonical_bytes(raw))
    assert prepared.request.arguments["revision"] == 1
    assert prepare_invocation(canonical_bytes(prepared.request.model_dump(mode="json"))) == prepared
    # Independent literal serialization for the Core request preimage. All
    # values in this fixture are ASCII/integers; compact sorted JSON equals JCS.
    preimage = json.dumps(
        {"capability_id": PLANNER, "arguments": prepared.request.arguments},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    assert prepared.request_digest == "sha256:" + hashlib.sha256(preimage).hexdigest()
    raw["arguments"]["revision"] = 2
    assert prepare_invocation(canonical_bytes(raw)).request_digest != prepared.request_digest


@pytest.mark.parametrize(
    "raw",
    [
        b'{"protocol_version":1,"protocol_version":1}',
        b'{"protocol_version":true,"capability_id":"x","arguments":{}}',
        b'{"protocol_version":1,"capability_id":"creator.missing@1.0.0","arguments":{}}',
        b'{"protocol_version":1,"capability_id":"creator.plan_content_portfolio@1.0.0","arguments":{}}',
        b"[1,2]",
        b" " * (MAX_BYTES + 1),
    ],
)
def test_invalid_preparation_refuses(raw):
    with pytest.raises(ValueError):
        prepare_invocation(raw)


def machine_discovery(bound, *args):
    with tempfile.TemporaryFile() as stream:
        stream.write(canonical_bytes(bound))
        stream.seek(0)
        return subprocess.run(
            [
                sys.executable,
                "-I",
                "-m",
                "zeo_core.adapters.runtime_host",
                *args,
                "--binding-fd",
                str(stream.fileno()),
            ],
            pass_fds=(stream.fileno(),),
            capture_output=True,
            timeout=20,
        )


def test_static_discovery_is_paginated_and_never_imports_the_factory():
    data = binding().model_dump(mode="json")
    data["factory"] = "module_that_must_not_be_imported:factory"
    ids = []
    for offset in (0, 20):
        proc = machine_discovery(data, "capabilities", "list", "--offset", str(offset), "--json")
        assert proc.returncode == 0, proc.stderr
        page = json.loads(proc.stdout)
        ids.extend(
            f"{m['id']['namespace']}.{m['id']['name']}@{m['id']['version']}"
            for m in page["capabilities"]
        )
        assert page["next_offset"] == (20 if offset == 0 else None)
    assert ids == sorted(c.definition.id.canonical() for c in capability_registry().list_all())
    described = machine_discovery(data, "capabilities", "describe", PLANNER, "--json")
    assert json.loads(described.stdout)["capability"]["id"]["name"] == "plan_content_portfolio"
    doctor = machine_discovery(data, "doctor", "--json")
    assert json.loads(doctor.stdout)["authorized"] is False


@pytest.mark.parametrize("defect", ["duplicate", "invalid_example", "digest", "oversize"])
def test_invalid_inventory_refuses_before_import(defect):
    data = binding().model_dump(mode="json")
    if defect == "duplicate":
        data["manifests"].append(data["manifests"][0])
    elif defect == "invalid_example":
        data["manifests"][0]["examples"][0]["request"] = {}
    elif defect == "oversize":
        data["manifests"][0]["description"] = "x" * MAX_BYTES
    else:
        data["manifest_digest"] = digest("wrong")
    proc = machine_discovery(data, "doctor", "--json")
    assert proc.returncode == 8
    assert json.loads(proc.stdout)["state"] == "protocol_error"


def exercise_host(tmp_path: Path, scenario: str):
    capability_id = "creator.research_synthesis@1.0.0" if scenario == "missing_service" else PLANNER
    raw = invocation(capability_id)
    prepared = prepare_invocation(canonical_bytes(raw))
    attempt = AttemptBinding(
        organization_id=raw["arguments"]["organization_id"],
        project_id="test-project",
        seat_id="test-seat",
        runtime_binding_id="test-runtime",
        packet_id="test-packet",
        operation_id="test-operation",
        attempt_id="test-attempt",
        fencing_generation=1,
        capability_id=capability_id,
        request_digest=prepared.request_digest,
        manifest_digest=binding().manifest_digest,
    )
    context = LaunchContext(
        protocol_version=1,
        provider=binding(),
        attempt=attempt,
        bootstrap_id="test-bootstrap",
        admitted_capabilities=(capability_id,),
        deadline_unix_ms=int(time.time() * 1000) + 30_000,
        workspace=str(tmp_path),
    ).model_dump(mode="json")
    if scenario == "changed_request":
        raw["arguments"]["revision"] = 9
    elif scenario == "wrong_organization":
        context["attempt"]["organization_id"] = "another-organization"
    elif scenario == "wrong_scope":
        context["admitted_capabilities"] = []
    elif scenario == "expired":
        context["deadline_unix_ms"] = 1
    elif scenario == "wrong_version":
        context["provider"]["version"] = "0.0.0"
    elif scenario == "wrong_python":
        context["provider"]["python_version"] = "3.0.0"
    elif scenario == "invalid_request":
        raw["arguments"]["profiles"] = []
    elif scenario == "domain_failure":
        raw["arguments"]["organization_id"] = "another-organization"
        context["attempt"]["organization_id"] = "another-organization"
        context["attempt"]["request_digest"] = prepare_invocation(
            canonical_bytes(raw)
        ).request_digest
    context_model = LaunchContext.model_validate_json(canonical_bytes(context))
    expected = context_model.attempt
    messages, artifacts, errors = [], [], []
    parent, child = socket.socketpair()
    parent.settimeout(15)

    def read_exact(size):
        data = bytearray()
        while len(data) < size:
            chunk = parent.recv(size - len(data))
            if not chunk:
                raise EOFError
            data.extend(chunk)
        return bytes(data)

    def peer():
        try:
            while True:
                size = struct.unpack("!I", read_exact(4))[0]
                assert 0 < size <= MAX_BYTES
                message = json.loads(read_exact(size))
                assert message["binding"] == context["attempt"]
                assert message["sequence"] == len(messages) + 1
                messages.append(message)
                method = message["method"]
                state, data = "allowed", {}
                if method == "bootstrap":
                    ordered = copy.deepcopy(context)
                    ordered["provider"]["manifests"] = manifest_inventory(
                        context_model.provider.manifests
                    )
                    assert message["payload"] == {
                        "pid": proc.pid,
                        "bootstrap_id": context["bootstrap_id"],
                        "launch_digest": digest(ordered),
                    }
                    if scenario == "bootstrap_refused":
                        state = "refused"
                elif method == "invoke.admit":
                    assert (
                        digest(
                            {
                                "capability_id": capability_id,
                                "arguments": message["payload"]["arguments"],
                            }
                        )
                        == expected.request_digest
                    )
                    if scenario in {"revoked", "cancelled", "waiting"}:
                        state = {
                            "revoked": "refused",
                            "cancelled": "cancelled",
                            "waiting": "waiting_approval",
                        }[scenario]
                elif method == "result.publish":
                    response = PlanContentPortfolioResponse.model_validate(
                        message["payload"]["data"]
                    )
                    assert response.plan.organization_id == expected.organization_id
                    assert response.plan.assignments
                    assert {a.publication_id for a in response.plan.assignments} <= {
                        p["publication_id"] for p in raw["arguments"]["profiles"]
                    }
                    assert digest(message["payload"]["data"]) == message["payload"]["data_digest"]
                    if scenario == "publication_refused":
                        state = "refused"
                    elif scenario == "lost_publication_reply":
                        return
                    else:
                        # Candidate artifact bytes are validated above; only the
                        # test peer's accepted reference reaches the host result.
                        artifact = tmp_path / "accepted-result.json"
                        with artifact.open("xb") as stream:
                            stream.write(canonical_bytes(message["payload"]["data"]))
                        artifacts.append(artifact)
                        data = {
                            "data_digest": message["payload"]["data_digest"],
                            "artifact_refs": ["test-artifact:portfolio"],
                        }
                        if scenario == "wrong_artifact_digest":
                            data["data_digest"] = digest("wrong")
                        elif scenario == "empty_artifact_refs":
                            data["artifact_refs"] = []
                else:
                    raise AssertionError(f"unexpected protected effect: {method}")
                reply = {
                    "protocol_version": 1,
                    "sequence": message["sequence"],
                    "host_nonce": message["host_nonce"],
                    "binding": message["binding"],
                    "request_digest": digest(message),
                    "state": state,
                    "data": data,
                }
                if scenario == "stale_reply":
                    reply["binding"] = {**reply["binding"], "fencing_generation": 2}
                encoded = canonical_bytes(reply)
                parent.sendall(struct.pack("!I", len(encoded)) + encoded)
        except EOFError:
            pass
        except BaseException as exc:
            errors.append(exc)
        finally:
            parent.close()

    with tempfile.TemporaryFile() as stream:
        stream.write(canonical_bytes(context))
        stream.seek(0)
        proc = subprocess.Popen(
            [
                sys.executable,
                "-I",
                "-m",
                "zeo_core.adapters.runtime_host",
                "invoke",
                "--context-fd",
                str(stream.fileno()),
                "--runtime-fd",
                str(child.fileno()),
            ],
            pass_fds=(stream.fileno(), child.fileno()),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=tmp_path,
        )
        child.close()
        worker = threading.Thread(target=peer, daemon=True)
        worker.start()
        try:
            stdout, stderr = proc.communicate(canonical_bytes(raw), timeout=30)
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()
            worker.join(timeout=16)
        assert not worker.is_alive()
        assert not errors, errors
        assert stderr == b""
        assert len(stdout.splitlines()) == 1
    return parse_result(stdout, proc.returncode, expected), messages, artifacts


@pytest.mark.parametrize(
    "scenario,state,methods",
    [
        ("success", "succeeded", 3),
        ("changed_request", "refused", 1),
        ("wrong_organization", "refused", 1),
        ("wrong_scope", "refused", 0),
        ("expired", "timed_out", 0),
        ("wrong_version", "protocol_error", 1),
        ("wrong_python", "protocol_error", 1),
        ("invalid_request", "invalid_request", 1),
        ("domain_failure", "failed", 2),
        ("bootstrap_refused", "refused", 1),
        ("revoked", "refused", 2),
        ("cancelled", "cancelled", 2),
        ("waiting", "waiting_approval", 2),
        ("stale_reply", "protocol_error", 1),
        ("missing_service", "unavailable", 1),
        ("publication_refused", "refused", 3),
        ("lost_publication_reply", "protocol_error", 3),
        ("wrong_artifact_digest", "protocol_error", 3),
        ("empty_artifact_refs", "protocol_error", 3),
    ],
)
def test_real_installed_host_invokes_creator_with_truthful_results(
    tmp_path, scenario, state, methods
):
    result, messages, artifacts = exercise_host(tmp_path, scenario)
    assert result.state == state
    assert len(messages) == methods
    assert result.effect_disposition == "none"
    if state == "succeeded":
        assert result.artifact_refs == ("test-artifact:portfolio",)
        assert artifacts[0].is_file()
        assert result.data is None  # the accepted artifact is retrieved through Runtime
    else:
        assert result.artifact_refs == ()


def test_provider_cli_matches_library():
    proc = subprocess.run(
        [sys.executable, "-I", "-m", "zeo_creator.cli", "runtime-provider"],
        check=True,
        capture_output=True,
        timeout=20,
    )
    assert proc.stdout == canonical_bytes(provider_inventory()) + b"\n"
