# ADR 0002: Zeocore 0.11.0 and the shared Runtime host

- Status: Accepted for Creator implementation; cross-system acceptance pending
- Date: 2026-09-10
- Decision owner: Creator Principal under Operator upgrade instruction
- Supersedes: ADR 0001's dependency pin only
- Pin superseded: the exact pin is now `zeocore[runtime-host]==0.18.0` (0.15.0 by PR #24, then 0.18.0), moved by PR #24 and approved by the council on 2026-10-12; ADR 0003 records the qualification. The rest of this decision stands.

Creator 0.5.4 consumes exactly `zeocore[runtime-host]==0.11.0`, retaining Python
3.14+, its 29 canonical capability identities, and all business schema versions.
The released Core host now provides the shared execution boundary. Creator's
existing explicit registry factory is its provider factory; Creator does not
add its own invoke CLI, MCP server, HTTP endpoint or authority verifier.

The installed provider exports canonical inventory and normalized request
preparation. Runtime selects and verifies the environment, admits the exact
operation, supervises Core's host, and accepts immutable artifacts. Scope
selection never changes the factory's admitted full inventory. Creator does
not infer authority from a local binding document or an environment digest.

The real portfolio planner is the first integration capability. The two
acquisition capabilities retain their service requirements and remain
unavailable under Core's current host until reviewed service injection exists.
No hidden credential fallback or silent capability removal is introduced.

Source gates and installed-wheel subprocess conformance cover the upgraded
dependency and provider boundary. Real Runtime supervision and agent acceptance
remain distinct evidence. See the [integration guide](../guides/runtime-host.md).
ADR 0001 remains the historical 0.5.3 record and continues to describe the
separation of Creator domain logic from authority, credentials and execution.
