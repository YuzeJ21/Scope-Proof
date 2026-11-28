# Final v0.2.9 Publication Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Rebuild final-version 0.2.9 archives and assemble a verified publication-review handoff.

**Architecture:** Reuse the existing candidate workflow and strict manifest. Keep release notes
in tracked source and exact observed asset identities in the enclosing PR.

**Tech Stack:** Existing Python, pytest, Pydantic, Hatch/uv and GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-11-27-v029-publication-review-design.md`

## Global Constraints

- Version 0.2.9 remains unpublished; public v0.2.8 stays the default download.
- No tag, Release, Pages deployment, outreach, adoption credit or new product feature.
- Preserve old candidate/example/frozen bytes and saved-record/evidence/gate behavior.
- Source/archive/test/installation identities remain bound by the existing strict manifest.

## Review Focus

- Development archive bytes must not be accepted as a final rebuild or modified in place.
- Current-source docs must not imply that final v0.2.9 is publicly available.
- Controlled archive fixtures must still exercise metadata/inventory/CLI rejection cases.
- PR preview identities must not stand in for the independently rebuilt main packet.
- Final release notes must distinguish implemented changes from constructed engineering evidence.

### Task 1: Prepare final source identity and review notes

**Files:** Version source, active README/roadmap/version guides, changelog, candidate helper
README copy, `tests/test_evaluation_candidate.py`, existing source-version contract, and
`docs/releases/v0.2.9-publication-review.md`.

**Interfaces:** Preserve `prepare_candidate(...) -> CandidateManifest`, all existing manifest
fields and the five-file CI packet. Fixture versions use current source by default; one explicit
old-development fixture exercises refusal without modifying its bytes.

- [x] Generalize archive fixtures and add the old-development refusal test. Observe RED before bump.
- [x] Advance version to 0.2.9, align active source docs and generic packet publication guidance.
- [x] Write release notes and publication-review instructions; retain historical provenance.
- [x] Pass affected tests, lint, frozen-path and whitespace checks; commit.

### Task 2: Review, integrate and retain final-version main packet

**Interfaces:** Consume Task 1 source through unchanged CI; record actual observed source,
archive hashes, CI attempt and artifact in the PR.

- [x] Run one fresh whole-branch review and fix important findings with RED/GREEN coverage.
- [ ] Sync an exact-tree PR and pass protected full/installed/browser/platform checks.
- [ ] Merge verified source, verify resulting main and its new 0.2.9 packet, and record exact
  artifacts and next decision in the PR. Stop before publication or additional feature work.
