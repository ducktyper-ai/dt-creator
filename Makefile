.PHONY: help setup sync test lint typecheck format check verify clean lock update \
	cli version doctor capabilities reference reference-check docs docs-serve examples \
	digest-vectors dist-check release-check install verify-publication-core

UV ?= uv
NODE ?= node
ZEO_CREATOR := $(UV) run zeo-creator
ARGS ?=
VERSION ?=

help:
	@echo "ZEO Creator — capability package diagnostics"
	@echo ""
	@echo "  make setup          Install the exact locked environment"
	@echo "  make verify         Lint, strict type-check, and test"
	@echo "  make doctor         Verify Python/Zeocore/manifests/projections"
	@echo "  make capabilities   List the public capability catalog"
	@echo "  make reference      Regenerate JSON schemas and neutral samples"
	@echo "  make docs           Build the documentation site in strict mode"
	@echo "  make docs-serve     Serve docs locally with live reload"
	@echo "  make examples       Run every public example"
	@echo "  make version        Show the installed distribution version"
	@echo "  make cli ARGS='…'   Invoke diagnostics directly"
	@echo "  make install VERSION=X.Y.Z  Install that PyPI release as a tool, then run doctor"

setup: sync

# Installs a published release, never this checkout. Rollback is the same target
# with the previous version.
install:
	@test -n "$(VERSION)" || { echo "make install needs VERSION=X.Y.Z" >&2; exit 2; }
	$(UV) tool install --force "zeocreator==$(VERSION)"
	zeo-creator doctor --json

sync:
	$(UV) sync --frozen

lock:
	$(UV) lock

update:
	$(UV) lock --upgrade
	$(UV) sync

cli:
	$(ZEO_CREATOR) $(ARGS)

version:
	$(ZEO_CREATOR) --version

doctor:
	$(ZEO_CREATOR) doctor --json

capabilities:
	$(ZEO_CREATOR) capabilities

reference:
	$(UV) run python -m scripts.export_reference_artifacts_v9

test:
	$(UV) run pytest -q

lint:
	$(UV) run ruff check --no-cache src tests scripts examples

typecheck:
	$(UV) run mypy src/zeo_creator examples

format-check:
	$(UV) run ruff format --check src tests scripts examples

format:
	$(UV) run ruff format src tests scripts examples

docs:
	$(UV) run mkdocs build --strict

docs-serve:
	$(UV) run mkdocs serve

examples:
	$(UV) run python examples/inspect_capabilities.py
	$(UV) run python examples/create_content_brief.py
	$(UV) run python examples/research_connector.py
	$(UV) run python examples/validate_and_prepare.py
	$(UV) run python examples/assess_performance.py
	$(UV) run python examples/complete_content_portfolio.py
	$(UV) run python examples/email_marketing.py
	$(UV) run python examples/runtime_portfolio.py

reference-check: reference
	git diff --exit-code -- reference src/zeo_creator/schemas src/zeo_creator/reference_artifacts src/zeo_creator/examples

check: format-check lint typecheck test reference-check docs

digest-vectors:
	node contracts/verify-digest-vectors.mjs
	node contracts/verify-email-digest-vectors-v1.mjs
	node contracts/verify-jcs-shared-vectors-v1.mjs

dist-check:
	rm -rf dist
	$(UV) build
	$(UV) run python -m scripts.check_distribution_v10
	$(UV) run python -m scripts.check_publication_core_distribution

release-check:
	$(UV) run python -m scripts.check_release_v1

verify-publication-core:
	$(NODE) packages/publication-core/tools/check-contract.mjs
	$(NODE) --test packages/publication-core/test/*.test.mjs

verify:
	@printf 'head: %s\n' "$$(git rev-parse HEAD)"
	$(MAKE) release-check verify-publication-core check digest-vectors dist-check

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache .coverage coverage.xml htmlcov dist build site
