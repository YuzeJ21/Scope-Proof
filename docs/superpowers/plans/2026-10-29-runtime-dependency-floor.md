# Runtime Dependency Floor Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans for coordinator execution with one
> independent whole-branch review. Measurements precede any metadata or source repair.

**Goal:** Resolve one version-bound runtime-floor compatibility and support-policy question.

**Architecture:** Verified public wheel in isolated Python 3.11, exact direct floors in one
transaction, recorded installed identities/dependencies. Existing trusted constructed journeys
guide a minimal conditional repair and its focused regression.

**Tech Stack:** Python, uv, Pydantic, pytest, Streamlit, installed-wheel Chromium, protected CI.

**Spec:** `docs/superpowers/specs/2026-10-29-runtime-dependency-floor-design.md`

## Global Constraints

- Preserve released v0.2.4 bytes/tags, frozen research, all evidence decisions and gates.
- Preserve full CI suites, unrounded 95% floor, browser/compatibility checks and strict protected merge.
- Distinguish installability, API compatibility, test-harness compatibility and patch-policy support.
- No personal testing, qualifying reviews, target code, release, deployment, outreach or Stage 3 work.

## Review Focus

- One resolver transaction and actual installed versions must establish the tested combination.
- Tests must import installed package code, not accidentally borrow checkout code.
- Do not promote a resolver-permitted but policy-incompatible older stack as supported.
- Published metadata remains historical; a development repair cannot retroactively fix it.
- Use genuinely observed automated outcomes, never participant or runtime-correctness claims.

### Task 1: Rehearse the existing declared floors

- [ ] Verify public wheel/tag/hash and isolated Python 3.11 identity.
- [ ] Install exact direct floors together; record dependency compatibility and complete versions.
- [ ] Run installed CLI/benchmarks, persistence/exports and bounded workbench checks.
- [ ] Reconcile observed dependencies with primary-source/current repository patch policy.

### Task 2: Close only a supported finding and integrate

- [ ] If justified, write a meaningful regression, observe failure and implement a narrow repair.
- [ ] Verify the repaired boundary independently; add an existing-lane check only if justified.
- [ ] Record version-bound findings/limits; refresh current documentation without rewriting history.
- [ ] Run relevant checks, full suite/95%, lint, benchmarks and package/browser/compatibility CI.
- [ ] Independent review, resolve supported findings, guarded merge and verify main; stop.
