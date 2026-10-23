# Contract API

ZEO Creator ships its versioned JSON Schemas inside the wheel and commits copies
under [`reference/schemas`](https://github.com/zeroemployeeorg/dt-creator/tree/main/reference/schemas).

```console
zeo-creator contracts list --json
zeo-creator contracts export --output=./schemas
zeo-creator contract-schema --name=content-brief --version=1
```

Every catalog entry contains the stable name, contract major, filename, and RFC
8785 canonical SHA-256 digest. Consumers should pin both the contract name and
major, then verify the digest before accepting an exported schema.

## Compatibility and version axes

ZEO Creator versions three surfaces independently:

| Axis | Example | Changes when |
|---|---|---|
| Package | `0.6.0` | Code, documentation, or bundled contracts are released |
| Capability | `creator.create_content_brief@1.0.0` | Request/response behavior or orchestration-facing semantics change |
| Contract schema | `content-brief@1` | Serialized contract compatibility changes |

Package releases may add implementations or documentation without changing a
capability or schema version. Backward-compatible schema additions remain within
the same major only when existing strict consumers can accept them; otherwise a
new schema major and filename are required. Capability IDs change independently
when the invocation contract or observable behavior is incompatible. The earlier
Git-only development line removed unsafe email preparation APIs without aliases;
its archived schemas remain available. Version 0.6.0 uses email v4. Pin versions
and follow explicit migration instructions for future incompatible changes.

## Publication and evidence

::: zeo_creator.contracts.publications

::: zeo_creator.contracts.evidence

## Editorial planning

::: zeo_creator.contracts.editorial

## Continuous newsroom interchange

::: zeo_creator.contracts.newsroom

## Commentary

::: zeo_creator.contracts.commentary

## Newsletter specialization

::: zeo_creator.contracts.newsletter

## Journalism integrity

::: zeo_creator.contracts.journalism

## Production boundary

::: zeo_creator.contracts.production

## Delivery and distribution

::: zeo_creator.contracts.delivery

::: zeo_creator.contracts.distribution

## Performance

::: zeo_creator.contracts.performance

## Common identity and canonicalization

::: zeo_creator.contracts.common

## Email marketing v1

The additive email family uses new contract names. Existing v1 newsletter,
`AudienceSelection`, performance and generic distribution schemas are unchanged.
All email references carry organization/publication, revision and digest.
`EmailEffectIntent` describes editorial intent; executable identities reference
public Zeocore `CapabilityId` values. Simulated example identities are not a
provider protocol and must never be used as live connector operations.

::: zeo_creator.contracts.email_marketing
