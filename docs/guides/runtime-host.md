# Call Creator through the shared Runtime host

Creator **0.6.0** installs Zeocore **0.18.0** and its `runtime-host` extra from
PyPI. Install the exact Creator release in a fresh environment. Upgrading from
0.5.3 also upgrades Core; do not override the older package's dependency pin.

## Install a pinned provider

Install from PyPI, then export the installed provider and sample request:

```console
uv venv --python 3.14 /tmp/creator-host
uv pip install --python /tmp/creator-host/bin/python "zeocreator==0.6.0"
/tmp/creator-host/bin/zeo-creator doctor --json
/tmp/creator-host/bin/zeo-creator runtime-provider > /tmp/creator-inventory.json
/tmp/creator-host/bin/python -m zeo_creator.examples.runtime_portfolio > /tmp/creator-request.json
```

The wheel declares `zeocore[runtime-host]==0.18.0`. Runtime must retain its
environment lock/image digest, verify wheel provenance, and pin the exact
interpreter patch version. The Unix inherited-descriptor host supports macOS
and Linux. Discovery preparation imports only the explicitly installed Creator
factory; execution uses Core's `zeo-capability` entry point.

| Provider field | Value |
| --- | --- |
| Distribution | `zeocreator` |
| Released version | `0.6.0` |
| Factory | `zeo_creator.registry:capability_registry` |
| Core dependency | `zeocore[runtime-host]==0.18.0` |
| Host protocol | `1` |
| First operation | `creator.plan_content_portfolio@1.0.0` |
| Expected response | `PlanContentPortfolioResponse`, containing `plan` |

`runtime-provider` emits a single compact canonical JSON inventory including
installed version, interpreter, factory, all 29 manifests, and the ordered
manifest digest. It deliberately omits environment identity, generation and
authority. It is provisioning metadata, not scoped agent discovery. Runtime
must validate the inventory in its pinned build environment and cache its
admitted static bytes. Live discovery uses the Core host without importing
provider code.

## Build the exact binding and request

The trusted Python provisioning step may use these public helpers:

```python
from zeo_creator.provider import prepare_invocation, provider_binding

# Values belong to the launcher; they never come from model arguments.
def prepare_for_runtime(verified_environment_digest, generation, request_bytes):
    binding = provider_binding(
        environment_digest=verified_environment_digest,
        generation=generation,
    )
    prepared = prepare_invocation(request_bytes)
    return binding, prepared.request, prepared.request_digest
```

Alternatively, Runtime appends its verified `environment_digest` and monotonic
`generation` to the inventory JSON to form Core's `ProviderBinding`. Include
the **entire** factory inventory: trimming it breaks the executable-candidate
comparison. Use `LaunchContext.admitted_capabilities` and scoped discovery to
restrict visibility and execution. All 29 manifests currently fit the 1 MiB
wire bound; Runtime must also bound the complete launch context and discovery
page. Empty admission authorizes nothing. Unknown exact capability IDs refuse.

`prepare_invocation` accepts strict Core `InvocationRequest` JSON: integer
`protocol_version: 1`, exact `capability_id`, and `arguments`. It validates
schemas and Creator business input, materializes defaults, and returns the
normalized request and Core digest. Duplicate keys, non-finite numbers,
over-limit input and unsupported IDs refuse. It never invokes a handler.

The Core digest preimage is exactly
`{"capability_id": ..., "arguments": ...}` after normalization, serialized
with Core's RFC 8785 canonicalizer. Do not hash raw input with missing defaults.
Do not substitute Creator's `content_digest`: Creator's artifact rules exclude
their own digest field and normalize timestamps differently. Runtime should
verify Core's shared vectors and the prepared request bytes in Go.

## Supervise and accept the real call

Runtime launches `zeo-capability invoke --request - --context-fd 3 --runtime-fd 4`.
The prepared request goes on stdin. Runtime supplies `LaunchContext` on a private
inherited descriptor and its connected Unix socket endpoint on another. Follow
the exact [Core 0.18.0 protocol](https://github.com/zeroemployeeorg/zeocore/blob/v0.18.0/docs/how-to/runtime-host.md),
including four-byte big-endian framing, message/reply binding and total deadlines.

1. `bootstrap`: Runtime verifies the actual supervised child, launch digest and
   current attempt/fence, and atomically consumes the one-use bootstrap ID.
2. `invoke.admit`: Runtime verifies normalized input, current scope, revocation,
   deadlines, requirements and the exact request and manifest digests.
3. Core imports the admitted installed factory and invokes the real Creator
   planner. The planner needs no filesystem, network, credentials or service.
4. `result.publish`: Runtime validates `PlanContentPortfolioResponse` against
   the admitted schema, verifies its Core data digest, stores an immutable
   scoped artifact, and returns matching `data_digest` and nonempty
   `artifact_refs`. Only then can the host return `succeeded`.

The host checks the top-level request organization against the attempt. Creator
checks internal publication and evidence consistency. Runtime must independently
authorize every input publication and artifact reference, not just the outer
organization. Arbitrary imports or local example contexts are not managed grants.

Core's final envelope carries Runtime-issued artifact references; it does not
inline the plan. Runtime retrieves and validates the stored response, including
Creator's nested artifact digests, before presenting its assignments to the
agent. A successful exit alone is insufficient. Parse the envelope on every
exit code and verify its exact attempt binding and state transition. Approval
waits stay pending. Rejected publication stays refused. A missing reply does
not authorize a second invocation: query the durable operation first.

## Capability availability

The catalogue retains all 29 public identities. Twenty-seven transformations
need no injected service; their `read` effect declaration is Core's conservative
classification of supplied-input computation. They do not send or schedule.

| Capability | Required injection | Core v1 host disposition |
| --- | --- | --- |
| `creator.research_synthesis@1.0.0` | `creator.evidence_source`, network | `unavailable` |
| `creator.assess_performance@1.0.0` | `creator.metrics_source`, network | `unavailable` |

Core's first host injects only `runtime.effects`. Listing either missing service
in a launch document cannot instantiate it. Existing direct Python integrations
can supply the documented ports; managed support needs a reviewed Core/Runtime
injection binding. Canonical email assessment consumes already-collected input.

## Evidence and remaining end-to-end acceptance

`tests/test_runtime_host.py` launches the actual installed Core host and Creator
factory in subprocesses. Its explicitly labelled IPC test peer exercises the
planner, validates/stores a plan artifact, and checks scope, digest, expiry,
version, revocation, missing-service, domain-error and publication refusals.
The same tests can be copied outside the checkout and run against the wheel.
They establish Creator/Core conformance, not a deployed Runtime controller.

Runtime still owns the real Go-supervised planner proof, durable artifact
retrieval, same-operation recovery, cancellation/fencing, and a scoped managed
agent turn. A test peer, an offline request example or an imported package
cannot satisfy those acceptance conditions. No live provider effect is part
of this pure-planner integration.
