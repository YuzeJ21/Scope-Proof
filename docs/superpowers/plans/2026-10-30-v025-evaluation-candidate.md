# v0.2.5 Evaluation Candidate Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans inline, with one independent whole-branch
> review. Use current native release/distribution patterns; do not implement a new publisher.

**Goal:** Prepare verified private v0.2.5 evaluation archives while public install stays v0.2.4.

**Architecture:** One source-version identity, unchanged runtime policy, version-bound guidance,
direct/source-built distribution comparison and an exact-main private evidence packet.

**Tech Stack:** Python, hatchling/uv, Pydantic, installed CLI/Chromium and protected GitHub CI.

**Spec:** `docs/superpowers/specs/2026-10-30-v025-evaluation-candidate-design.md`

## Global Constraints

- Source/candidate **0.2.5, unreleased**; public install/constants/downloads remain **v0.2.4**.
- Preserve published v0.2.3/v0.2.4 guards, old records/results, frozen R-002 and required checks.
- Preserve schemas, deterministic gates, criteria confirmation, reviewer decisions and dependencies.
- No tag, Release, upload, deployment, outreach, personal testing, qualifying reviews or Stage 3.

## Review Focus

- Candidate identity must not imply public availability or rewrite released/historical identities.
- Existing published-final guards must remain effective for both v0.2.3 and v0.2.4.
- Source archive must carry the same runtime files, policy, corpus and requirements as direct wheel.
- Reopening an old review must not relabel its producer or fabricate acceptance/history.
- Final private archives must bind the actual resulting main, not only the PR test head.

### Task 1: Prepare and integrate candidate identity

- [ ] Update the existing candidate identity expectation, observe failure, then advance source;
      align active guidance and add candidate notes while retaining published constants/guards.
- [ ] Run focused contracts, identity/upgrade tests, lint, lock checks and constructed benchmarks.
- [ ] Build/test preliminary archives and source-built parity outside the checkout. Record limits.
- [ ] Run covered full suite, independent review and required exact-head CI; guarded merge/main.

### Task 2: Verify exact-main candidate bytes

- [ ] Build fresh direct wheel/source archive from clean resulting main; retain source/tree,
      member inventories, SHA-256 values and checksum manifest with Pydantic validation.
- [ ] Install each path outside checkout, verify installed identities/dependencies and both
      benchmarks, and exercise installed workbench/browser behavior with constructed actors.
- [ ] Complete native v0.2.4 writer → candidate reader rehearsal without altering original data.
- [ ] Review evidence, distinguish completed/pending publication checks, preserve exact private
      artifacts and stop. Report the separate publication gate; do not perform it.
