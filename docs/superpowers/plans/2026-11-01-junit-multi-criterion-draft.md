# Multi-criterion JUnit Draft Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Explicitly stage multiple criterion mappings from one JUnit artifact before a single import.

**Architecture:** A typed pure-core session draft binds the complete validated review and artifact. A small workbench renderer stages/removes mappings and returns a candidate through the existing builder; existing append and persistence remain unchanged.

**Tech Stack:** Python3.11+, Pydantic2, Streamlit/AppTest, pytest/Playwright.

**Spec:** docs/superpowers/specs/2026-11-01-junit-multi-criterion-draft-design.md

## Global Constraints

- At most5,000 canonical selector pairs; existing1MiB XML/100suites/5,000cases/20,000elements unchanged.
- Preserve duplicate-artifact rejection, single-owner test cases, parser/lifecycle, savedv7 and frozen R-002.
- Draft preview/staging is organizational non-gating context, not execution/correctness/acceptance.
- Full validated state fingerprint + actual artifact digest bind every draft operation.
- No personal testing, qualifying reviews, release/deployment/outreach, genuine-use or Stage3 credit.
- Source unreleased0.2.5, publicv0.2.4 unchanged.

## Review Focus

- Same suite/case IDs from replacement bytes must not retain assignments.
- A rejected overlapping stage must not discard or partly apply previous valid mappings.
- A saved-state change limited to acceptance/notes/provenance must expire draft authority.
- Unsubmitted target/scopes must not silently join or be ignored by final Save.
- Existing reset and pending-input guards must include staged mappings, even when selectors are empty.

### Task 1: Pure typed mapping draft

**Files:** Create scopeproof_core/importers/junit_draft.py, tests/importers/test_junit_draft.py; independent tests/importers/test_junit_draft_safety.py.

**Interfaces:** `JUnitMappingDraft` and four functions exactly as design; selections tuple of existing JUnitMappingSelection. Final build returns existing JUnitEvidenceImport. Reuse parse_junit_artifact/build_junit_evidence_import and full state fingerprint, no core policy edits.

- [ ] Write failing behavior tests: two distinct criteria in one import; overlap leaves prior draft unchanged; same-target union; criterion removal; stale artifact/fullstate; nested/model tampering; no saved truth mutation.
- [ ] Run `.venv/bin/python -m pytest -q tests/importers/test_junit_draft.py`; expect missing-feature failures.
- [ ] Implement bounded typed draft and helpers; run new core/safety plus existing tests/importers/test_junit.py, expect pass.
- [ ] Commit core/tests/spec/plan.

### Task 2: Explicit workbench draft and installed flow

**Files:** Create apps/web/junit_mapping.py, tests/apps/test_junit_mapping.py; modify apps/web/app.py, existing JUnit cases in tests/apps/test_streamlit_app.py, tests/browser/test_packaged_workbench.py, .github/workflows/ci.yml, README.md, ROADMAP.md, docs/releases/v0.2.3-status-and-next-stages.md; add dated audit.

**Interfaces:** `render_junit_mapping_draft(state, artifact_bytes, parsed, *, scope_ids, scope_labels, importer, limitations) -> JUnitEvidenceImport | None`; `clear_junit_mapping_draft()` resets typed draft/target/scopes/removal controls before widgets. App retains existing parser/uploader/sanitized preview and final append/save/reset logic. Only staged choices are returned; Add and Remove/Clear cause rerun with dependent control reset.

- [ ] Write failing AppTest cases for explicit target/stage, staged multi-criterion preview, overlap rejection, group removal/clear, source/review reset, invalid upload and no implicit save.
- [ ] Run AppTest file for RED, implement renderer/integration and include new draft in pending/global reset guards; expect GREEN.
- [ ] Update old single-criterion tests/browser action sequence to choose target and stage, retaining original assertions. Extend installed journey to prove two mappings/reopen/export and unchanged gate/runtime truth. Collect17 browser checks unchanged.
- [ ] Add new core/safety/AppTest cases to Windows bounded verification. Update documentation/outcome boundaries; commit.
- [ ] Run full covered suite with95% unrounded floor, lint/lock/diff, deterministic benchmarks, fresh installed browser and CLI checks. Fresh whole-branch independent review; resolve supported findings with regressions, no frozen rewrites.
- [ ] Create/attach PR, wait exact-head CI/CodeQL/reviews, expected-head squash merge; verify entire resulting tree and mainCI/CodeQL, clean/sync checkouts. Archive only owned ledger, complete goal with actual elapsed time/results/limits.
