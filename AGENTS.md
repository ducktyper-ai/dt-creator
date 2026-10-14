# ZEO Creator agent entrypoint

ZEO Creator is a governed capability package, not a workflow runtime.

- Preserve publication identity and evidence provenance end to end.
- Keep credentials and provider SDKs outside contracts, capabilities, and services.
- Never add live provider execution, scheduling, OAuth, or renderer internals.
- Use `make verify` and `make doctor` before declaring work ready.
- Do not publish, push to the golden repository, rename, or change repository visibility without an explicit operator decision. Work on a fork and open a pull request.

Governed work lives in the associated organization corpus and must follow its
active statement of work.

To propose or contribute a change, read [CONTRIBUTING.md](CONTRIBUTING.md): how to propose, what
is welcome, the owner-only areas, how to build and submit, and the maintainer's response times.
