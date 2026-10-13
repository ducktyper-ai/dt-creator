# ADR 0003: Bounded, qualified Zeocore compatibility

- Status: the bounded range is Proposed and not in force; the exact pin it would replace is now `==0.18.0`
- Date: 2026-10-09; updated 2026-10-12
- Decision owner: Creator seat, under the council's K4 direction of 2026-10-09
- Supersedes, once accepted: ADR 0002's exact dependency pin only
- Pin successor: the retained `==0.11.0` pin moved to `==0.15.0` in PR #24, approved by the council on 2026-10-12, and then to `==0.18.0` in PR #31 (both sensitive, dependency changes)

The council retained Creator's exact `zeocore[runtime-host]==0.11.0` pin until a
successor decision is reviewed. That successor was PR #24 (`==0.15.0`, approved by the council on
2026-10-12), and Creator now pins exactly `zeocore[runtime-host]==0.18.0` (PR #31). The pin is
still exact; the bounded range below remains a proposal. The council also adopted bounded, qualified compatibility
as the direction. Applications lock exact environments; a library should not
demand one global Zeocore release. Creator has no hosted or Broker coupling, so
a Zeocore release made for hosted integrations should not force every Creator
consumer through a Creator release.

## Proposed decision

Creator declares a bounded Zeocore range, not one version. The lower bound is the
oldest release that Creator's gate has qualified. The upper bound excludes the
minor after the newest **qualified** minor (for example `>=0.11.0,<0.15` once
0.14.0 qualifies). Zeocore's 0.x minors may break and it has shipped no patch
releases, so a "below the next minor" bound would admit exactly one version.
The range is only a ceiling: a release inside it is admitted only when Creator's
gate has qualified it, and the qualified list is the admission rule.

Compatibility is also bounded by the runtime-host protocol version. Every
runtime-host message carries `protocol_version` (1 today), and Zeocore treats a
change to it as breaking. A Zeocore release whose protocol version differs from
the qualified one is not admitted, whatever its package version. The wheel does
not ship the protocol's schemas or canonical vectors, so their sha256 values are
pinned from the source tree at the qualified tag.

Qualification covers only the Zeocore surface Creator actually uses:

- `zeo_core.tools`: `ToolContext`, `capability`, `invoke_sync`,
  `BoundCapability`, `CapabilityRegistry`, `bound_capability_of`;
- `zeo_core.contracts`: `CapabilityExample`, `CapabilityResult`, `EffectKind`,
  `CapabilityId`, `CapabilityRequirements`, `NetworkRequirement`,
  `CapabilityManifest`;
- `zeo_core.contracts.runtime`: `InvocationRequest`, `ProviderBinding`;
- `zeo_core.adapters.runtime_host`: `host.prepare_request`,
  `catalogue.validate_inventory`, and `canonical.canonical_bytes`, `digest`,
  `manifest_inventory`, `parse_json`, `MAX_BYTES`, `InvalidRequestError` and
  `ProtocolError`;
- `zeo_core.adapters.llm_tools`: `OpenAIFunctionTool`, `project_openai_tool`.

Creator's tests also use a gate surface, which qualification covers too:
`catalogue.CandidateCatalogue`, `host.parse_result`,
`contracts.CapabilityStatus`, and `contracts.runtime.AttemptBinding` and
`LaunchContext`. The list is measured by parsing every `zeo_core` import in
`src/` and `tests/`, not by line matching, which misses multi-line imports.

The Zeocore seat reviewed this surface on 2026-10-09 (ZEOCORE-SOW-02), and
its tiers carry different risk:

- **Public (20 names):** in a package `__all__` and documented. These are all of
  `tools`, all of `contracts` plus `CapabilityStatus`, all of `contracts.runtime`,
  and `llm_tools`.
- **Documented, no `__all__` (1 name):** `host.parse_result` (test-only).
- **Internal through 0.14.0 (10 names):** `host.prepare_request`,
  `catalogue.validate_inventory` and `CandidateCatalogue`, and every `canonical`
  name above. Zeocore's policy let internal names change in any release, including
  a patch, and 9 of them are in `provider.py`. Zeocore 0.15.0 promotes all of them
  (see "Resolved at Zeocore 0.15.0"), so from the `==0.15.0` pin onward they are a
  supported tier. Before 0.15.0 they were qualified per release, with the shared
  RFC 8785 vectors run against `canonical_bytes` from the installed wheel.

A Zeocore release qualifies when, installed in a clean environment, it passes:

- the full `make verify`;
- `make doctor`;
- the installed-wheel host conformance;
- an unchanged canonical provider inventory;
- an unchanged contract catalog, so every schema digest stays the same.

The CI matrix runs the gate at the range's lower bound and at the newest
qualified release. A newly published Zeocore is added to the matrix by a reviewed
change. The runtime check in `provider.py` and the doctor check accept a version
only if it is inside the declared range **and** in the qualified list. Neither
check simply compares against one string.

## Protocol pins at the current releases

These are the sha256 values of `contracts/runtime-host-v1/` in Zeocore's source
tree, measured on 2026-10-09. They are identical at `v0.11.0` (`4fb6dc9c`, the
released 0.5.4 pin) and `v0.12.0` (`ddbd9e0d`). Neither the 0.14.0 draft (#89, at
`4a4c8414` and `6fc21f8c`) nor the 0.15.0 draft (#90, `e41e3857`) changes the
directory, and the released `v0.15.0` (`f15d7222`) is byte-identical to `v0.11.0`
there (measured 2026-10-12). Qualifying a new release starts by
comparing against this table; any difference is a protocol change, not a
qualification.

| File | sha256 |
|---|---|
| `canonical-vectors.json` | `0a8e8ce9af01134181d464997c7dc9172bc9a468a261ce7f02232e712b75fdb5` |
| `effect-request.schema.json` | `ab0392af101d6f12ca92948135c2c25b7be67a85e6ad1f3e4b43e3c776758a66` |
| `host-result.schema.json` | `8c5a0b7770e8768fc9edbc105ed5f1600483e8d79d9fda66bc1dc6aa3a7f1368` |
| `invocation-request.schema.json` | `b0b746be0097dfbc3f8160915d1e092a1b71a61a6d308c7b7570c2089db29e46` |
| `launch-context.schema.json` | `5b2eccd9c379ad03cf42ea500edb0daee1d309e4352bae7037f0a7e86866b19f` |
| `provider-binding.schema.json` | `09bc9a713c1c784715580794cf6dfd682ce13dca460a889042b43b1cc46952f1` |
| `runtime-reply.schema.json` | `13e695f183212cc6898050d44c2088605af3ab81057cd9d9357bd3c6a8e8204e` |

## What does not change

- Creator owns no credentials, authority, scheduling, effects or retries
  (ADR 0001).
- Package versions and contract versions stay separate. A qualified Zeocore
  never changes a public contract digest without a new contract major.
- Runtime still verifies the exact environment it admits. A range in Creator
  widens what can be installed. It does not change what Runtime accepts.

## Open before acceptance

- The range syntax, and whether the qualified list is packaged data or derived
  from the range plus CI evidence.
- How Creator reads the protocol version. Zeocore 0.15.0 exports
  `zeo_core.contracts.runtime.RUNTIME_HOST_PROTOCOL_VERSION` (`1`), tested against
  every runtime-host-v1 schema and the vectors.

## Resolved at Zeocore 0.15.0

Zeocore 0.15.0 (PyPI, tag `v0.15.0`, wheel sha256 `894e4ca8…e629`) promotes the
internal tier. Installed in a clean environment on 2026-10-12, its `__all__` lists
contain every name Creator uses there: the seven `runtime_host.canonical` names,
`catalogue.CandidateCatalogue` and `validate_inventory`, and `host.prepare_request`
and `parse_result`. Creator's full `make verify` and `make doctor` pass against it,
with no source change beyond the pin. From 0.15.0 these names are a supported tier,
not qualified per release.

## Qualified at Zeocore 0.18.0 (2026-10-13)

Zeocore 0.16.0, 0.17.0, 0.17.1 and 0.18.0 are on PyPI. `contracts/runtime-host-v1/` is
byte-identical to 0.15.0's at every one of those tags. Creator's full `make verify` and `make doctor`
pass against 0.18.0, with the pin as the only change, and no reference artifact or contract digest
moves. Creator now pins `==0.18.0`. The bounded range above remains a proposal: Zeocore now
releases on every merge, so an exact pin needs a Creator PR per qualified release, and that cost is
the case for deciding the range.
