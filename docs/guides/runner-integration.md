# Integrate a controlling runner

ZEO Creator is deliberately runner-neutral. Sovereign Agent and a managed ZEO
runtime use the same capability registry, request models, and results.

## Managed Runtime host

For Creator 0.6.1 with Zeocore 0.28.0, use the
[shared host integration](runtime-host.md). It exports an exact installed
inventory and normalizes requests before Runtime admission. Production managed
invocation goes through Core's host and the live Runtime channel. The direct
Python construction below describes the library boundary, not an alternate grant.

## Discover capabilities

```python
from zeo_creator.registry import capability_registry

registry = capability_registry()
capability = registry.get("creator.research_synthesis@1.0.0")
```

For LLM tool surfaces:

```python
from zeo_creator.registry import openai_tool_projections

tools = openai_tool_projections()
```

Projection does not grant authority. It only translates the manifest into a
runner-compatible function description.

## Construct context

Production runners should construct `ToolContext` themselves. The convenience
`make_context` helper exists for examples and bounded local workflows.

Legacy v1 compatibility capabilities accept already-collected data through named ports:

| Capability | Required service |
|---|---|
| Research synthesis | `creator.evidence_source` |
| Performance assessment | `creator.metrics_source` |

Canonical email transformations require neither an acquisition service nor network access.
Collect and persist observations before invoking Creator.

## Keep runtime state outside artifacts

Persist capability results as revisioned artifacts, but keep these in the
runtime:

- commitments and schedules;
- retry and resumption state;
- approval state and approving principals;
- effect-authority grants;
- connector credentials;
- execution receipts and reconciliation workflow; and
- organizational policy decisions.

## Govern writes

`creator.prepare_distribution` returns a proposal whose `required_effects` are
`write` and `external_communication`. This describes what a later execution
would require. The capability itself declares no provider write and executes
nothing.

The runtime must authorize the exact operation fields covered by the approval
digest. A broad permission such as “may post to LinkedIn” is not equivalent to
approval of one artifact, payload, destination, and schedule.

## Failure behavior

- Missing required services produce Zeocore's unavailable result before domain
  logic runs.
- Domain policy failures return enumerated `ZEO_CREATOR_*` error codes.
- Invalid requests fail Pydantic validation before invocation.
- Provider and connection failures belong to the injected adapter/runtime layer.

Use these distinctions to decide whether to correct input, request approval,
retry an observation, or escalate operationally.
