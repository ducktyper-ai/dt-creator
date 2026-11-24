.PHONY: help help-all build hooks release-candidate release setup sync test lint typecheck format check verify clean lock update \
	cli version doctor capabilities reference reference-check docs docs-serve examples \
	digest-vectors dist-check release-check install verify-publication-core

UV ?= uv
NODE ?= node
ZEO_CREATOR := $(UV) run zeo-creator
ARGS ?=
VERSION ?=
# Build output. Point these outside the checkout (for example on a scratch volume)
# to keep the working tree free of builds; the defaults keep them in place.
DIST_DIR ?= dist
SITE_DIR ?= site

.DEFAULT_GOAL := help

help: ## Show this first-time guide (make help-all lists every target)
	@echo "ZEO Creator (zeocreator, import zeo_creator, CLI zeo-creator)"
	@echo "Creator-domain transformations over Zeocore contracts: research synthesis,"
	@echo "editorial planning, content briefs, delivery validation, distribution, performance."
	@echo "It owns no credentials, scheduling, provider writes or releases."
	@echo ""
	@echo "New here? Five targets:"
	@echo "  make doctor         Check your tools and environment (changes nothing)"
	@echo "  make setup          Install the exact locked environment"
	@echo "  make capabilities   See what the package offers"
	@echo "  make verify         THE GATE: what the build host runs before a merge"
	@echo "  make docs           Build the documentation site"
	@echo ""
	@echo "Useful next: make test | make lint | make typecheck | make build | make examples | make reference"
	@echo "Where things go: DIST_DIR (default dist) holds builds and SITE_DIR (default site) the docs; make clean removes both."
	@echo "Releases: make release-candidate and make release explain the route; releases are not cut from this repository. Run the gate on the Linux build host."
	@echo "Git hooks: make hooks"
	@echo "Every target: make help-all"

help-all: ## List every target with its description
	@awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z0-9_-]+:.*## / {printf "  make %-24s %s\n", $$1, $$2}' $(MAKEFILE_LIST) | sort

setup: sync ## Install the exact locked environment (same as sync)

# Installs a published release, never this checkout. Rollback is the same target
# with the previous version.
install: ## Install a PyPI release as a tool (VERSION=X.Y.Z), then run its doctor
	@test -n "$(VERSION)" || { echo "make install needs VERSION=X.Y.Z" >&2; exit 2; }
	$(UV) tool install --force "zeocreator==$(VERSION)"
	zeo-creator doctor --json

sync: ## Install dependencies from the lockfile, never changing it
	$(UV) sync --frozen

lock: ## Re-resolve and write the lockfile
	$(UV) lock

update: ## Upgrade all dependencies, then sync
	$(UV) lock --upgrade
	$(UV) sync

cli: ## Run the zeo-creator CLI directly (ARGS='...')
	$(ZEO_CREATOR) $(ARGS)

version: ## Show the installed zeocreator version
	$(ZEO_CREATOR) --version

doctor: ## Check every prerequisite and report pass or fix lines; changes nothing
	@fail=0; \
	ok() { printf '  ok    %s\n' "$$1"; }; \
	bad() { printf '  FIX   %s\n' "$$1"; fail=1; }; \
	echo "Prerequisites (names and versions only; no secrets are read)"; \
	if command -v $(UV) >/dev/null 2>&1; then ok "uv $$($(UV) --version | cut -d' ' -f2)"; \
	else bad "uv not found: install it with: brew install uv"; fi; \
	if command -v git >/dev/null 2>&1; then ok "git $$(git --version | cut -d' ' -f3)"; \
	else bad "git not found: install git"; fi; \
	want=$$(tr -d ' \n' < .node-version 2>/dev/null); \
	if command -v $(NODE) >/dev/null 2>&1; then \
	  have=$$($(NODE) -v | sed 's/^v//'); \
	  if [ "$${have%%.*}" = "$${want%%.*}" ]; then ok "node $$have (.node-version $$want)"; \
	  else bad "node $$have, but .node-version wants major $${want%%.*}: install Node $$want"; fi; \
	else bad "node not found: install Node $$want (digest vectors and publication-core need it)"; fi; \
	if [ -x .venv/bin/python ]; then \
	  py=$$(.venv/bin/python -c 'import sys; print("%d.%d.%d" % sys.version_info[:3])'); \
	  if .venv/bin/python -c 'import sys; sys.exit(0 if sys.version_info >= (3, 14) else 1)'; then ok "python $$py (needs 3.14 or newer)"; \
	  else bad "python $$py in .venv, needs 3.14 or newer: run make setup after: uv python install 3.14"; fi; \
	else bad "python: .venv missing, so the version is unchecked: run make setup (needs Python 3.14 or newer)"; fi; \
	ok "checkout $$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo n/a)@$$(git rev-parse --short HEAD 2>/dev/null || echo n/a)"; \
	if [ -f uv.lock ]; then ok "uv.lock present"; else bad "uv.lock missing: restore it from git"; fi; \
	if [ -d .venv ]; then ok ".venv present"; else bad ".venv missing: run make setup"; fi; \
	echo "Package checks (zeo-creator doctor)"; \
	if [ -d .venv ]; then PYTHONDONTWRITEBYTECODE=1 .venv/bin/zeo-creator doctor --json || fail=1; \
	else echo "  skipped: needs .venv"; fi; \
	echo "Environment variables: none required. DIST_DIR and SITE_DIR are optional build-output paths."; \
	if [ $$fail -eq 0 ]; then echo "doctor: all prerequisites ok"; else echo "doctor: fix the lines above, then rerun"; exit 1; fi

capabilities: ## List the public capability catalog
	$(ZEO_CREATOR) capabilities

reference: ## Regenerate the JSON schemas and neutral samples
	$(UV) run python -m scripts.export_reference_artifacts_v9

test: ## Run the test suite
	$(UV) run pytest -q

lint: ## Run ruff lint
	$(UV) run ruff check --no-cache src tests scripts examples

typecheck: ## Run mypy in strict mode
	$(UV) run mypy src/zeo_creator examples

format-check: ## Check formatting without changing files
	$(UV) run ruff format --check src tests scripts examples

format: ## Format sources with ruff (changes files)
	$(UV) run ruff format src tests scripts examples

docs: ## Build the documentation site in strict mode (SITE_DIR)
	$(UV) run mkdocs build --strict --site-dir "$(abspath $(SITE_DIR))"

docs-serve: ## Serve the docs locally with live reload
	$(UV) run mkdocs serve

examples: ## Run every public example
	$(UV) run python examples/inspect_capabilities.py
	$(UV) run python examples/create_content_brief.py
	$(UV) run python examples/research_connector.py
	$(UV) run python examples/validate_and_prepare.py
	$(UV) run python examples/assess_performance.py
	$(UV) run python examples/complete_content_portfolio.py
	$(UV) run python examples/email_marketing.py
	$(UV) run python examples/runtime_portfolio.py

reference-check: reference ## Regenerate the reference and fail if it differs from the checkout
	git diff --exit-code -- reference src/zeo_creator/schemas src/zeo_creator/reference_artifacts src/zeo_creator/examples

check: format-check lint typecheck test reference-check docs ## Format check, lint, types, tests, reference check and docs build

digest-vectors: ## Verify the shared digest and JCS vectors with Node
	node contracts/verify-digest-vectors.mjs
	node contracts/verify-email-digest-vectors-v1.mjs
	node contracts/verify-jcs-shared-vectors-v1.mjs

dist-check: ## Build the wheel and sdist and check their contents (DIST_DIR)
	@test -n "$(DIST_DIR)" || { echo "DIST_DIR must not be empty" >&2; exit 2; }
	rm -rf "$(DIST_DIR)"
	$(UV) build --out-dir "$(DIST_DIR)"
	ZEOCREATOR_DIST_DIR="$(abspath $(DIST_DIR))" $(UV) run python -m scripts.check_distribution_v10
	ZEOCREATOR_DIST_DIR="$(abspath $(DIST_DIR))" $(UV) run python -m scripts.check_publication_core_distribution

build: ## Build the wheel and sdist into DIST_DIR (a local build; publishing is operator-only)
	$(UV) build --out-dir "$(DIST_DIR)"

hooks: ## Install the repository's git hooks (.githooks) if it defines any; changes only .git config
	@if [ -d .githooks ]; then git config core.hooksPath .githooks && echo "hooks: core.hooksPath set to .githooks"; \
	else echo "hooks: this repository defines no git hooks yet (.githooks is absent); nothing installed"; fi

release-candidate: ## Not run on a laptop: a candidate is built once on a Linux gate host from an exact commit (vX.Y.Z-rc.N)
	@echo "release-candidate: refused here. The candidate (wheel and sdist of an exact commit, checksums) is built once on a Linux gate host and uploaded with gh release as a pre-release." >&2
	@echo "Locally, make build shows what a build produces. Never run this on the Mac mini." >&2
	@exit 2

release: ## Not run from this repository: the approved candidate is promoted by the release process (vX.Y.Z)
	@echo "release: refused here. A release is the approved candidate promoted unchanged by the release process; it is never rebuilt or cut from this repository." >&2
	@exit 2

release-check: ## Check release consistency
	$(UV) run python -m scripts.check_release_v1

verify-publication-core: ## Check and test the bundled publication-core package
	$(NODE) packages/publication-core/tools/check-contract.mjs
	$(NODE) --test packages/publication-core/test/*.test.mjs

verify: ## THE GATE: release-check, publication-core, check, digest vectors, dist-check
	@printf 'head: %s\n' "$$(git rev-parse HEAD)"
	$(MAKE) release-check verify-publication-core check digest-vectors dist-check

clean: ## Remove caches and build output (DIST_DIR, SITE_DIR)
	rm -rf .pytest_cache .ruff_cache .mypy_cache .coverage coverage.xml htmlcov build "$(DIST_DIR)" "$(SITE_DIR)"
