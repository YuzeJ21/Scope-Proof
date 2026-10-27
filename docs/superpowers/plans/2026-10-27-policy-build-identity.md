# Policy and core-source identity implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Record an explicitly observed core-source fingerprint for new analyses while preserving unknown historical provenance.

**Architecture:** One core-only identity module defines the strict schema and canonical digest. Analysis entry points opt in; model defaults and validation never manufacture provenance.

**Tech Stack:** Python 3.11+, Pydantic 2, SHA-256, existing pytest and package checks.

**Spec:** `docs/superpowers/specs/2026-10-27-policy-build-identity-design.md`

## Global Constraints

- Scheme is `core-python-source-v1`; policy declaration is `2.0.0`.
- No gate predicate, migration policy, retrieval threshold or frozen R-002 changes.
- Absent identity stays unknown. Fingerprint is neither a signature nor execution attestation.
- No personal testing, qualifying reviews, outreach, release, deployment or licensing change.

## Review Focus

- Legacy objects missing the identity must remain unknown through parsing and reopening.
- Malformed digests and unexpected fields must be rejected by Pydantic.
- Equal source with different roots, creation order and CRLF/LF must hash identically.
- A changed source byte or path must change identity; bytecode must not.
- Wheel and checkout must observe equal core source; later validation must preserve recorded identity.

## Task 1: Core identity and analysis capture

**Files:** create `scopeproof_core/build_identity.py` and `tests/test_build_identity.py`; modify `scopeproof_core/schemas/models.py`, `scopeproof_core/cli.py`, `scopeproof_core/demo.py`, `apps/web/app.py`.

**Interfaces:** `CoreSourceIdentity` has `scheme` and `sha256`; `current_core_source_identity() -> CoreSourceIdentity`; `core_source_identity(root: Path) -> CoreSourceIdentity` implements the canonical manifest. `Review.analysis_source_identity` defaults to `None`.

`attach_analysis` adopts only incoming tool/policy/source metadata on confirmed reanalysis;
all non-metadata review identity checks remain exact and historical bundles remain unchanged.

- [ ] Write tests for the five review-focus cases and default/explicit identity round trips.
- [ ] Run focused tests and observe failure before implementation.
- [ ] Implement canonical source identity; capture only at new analysis creation.
- [ ] Run core, CLI, schema and lifecycle regressions; retain historical `tool_version` and ruleset metadata.

## Task 2: Export and operator contract

**Files:** modify `scopeproof_core/reporting/exporters.py`; create `tests/reporting/test_build_identity_exports.py` and `docs/development/engine-identity.md`.

- [ ] Write failing tests for recorded/unknown identity in JSON, Markdown, CSV and HTML.
- [ ] Implement rendering without changing evidence/gate behavior; clarify the workbench export caption.
- [ ] Document the exact manifest algorithm, policy history, excluded inputs and migration/revalidation semantics.
- [ ] Run export, storage and repository-contract tests, lint, full suite with 95% coverage, benchmarks and installed-package/browser checks.
- [ ] Obtain independent review; fix supported findings; commit and include exact-head CI evidence before integration.
