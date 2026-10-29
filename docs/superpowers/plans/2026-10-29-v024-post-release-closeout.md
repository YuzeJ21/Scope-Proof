# v0.2.4 Post-release Closeout Implementation Plan

> **For agentic workers:** Execute in this session with scoped documentation delegation and an
> independent whole-branch review before protected merge.

**Goal:** Reconcile current guidance and source identity with published v0.2.4, and retain public
verification evidence without changing released bytes or claiming external validation.

**Architecture:** Published v0.2.4 remains immutable at its release source. New source uses
`0.2.5.dev0`. A sanitized Pydantic-validated dated record anchors documentation to observed public
assets and engineering checks. Historical preparation/research records retain their meaning.

**Tech Stack:** Python, Pydantic, pytest, Ruff, uv, Markdown, GitHub protected checks.

**Spec:** `docs/superpowers/specs/2026-10-29-v024-post-release-closeout-design.md`

## Global Constraints

- Preserve released v0.2.4 bytes/tag/source and frozen research; no new publication or deployment.
- No personal testing, qualifying reviews, invented human evidence or Stage 3 advancement.
- No product behavior, dependency changes or speculative features.
- Merge only a reviewed exact head after hosted required checks; preserve old final-version guards.

## Review Focus

- Current install v0.2.4 must remain separate from unreleased `0.2.5.dev0` source.
- Dated v0.2.3/preparation records must not silently become claims about new source.
- Both published-final versions must still reject changed package inputs.
- Public records must contain no private paths and distinguish automation from independent use.
- The publication incident must be recorded without inventing a successful prepublication check.

### Task 1: Close out release guidance and identity

Files: `scopeproof_core/version.py`, `tests/test_repository_contracts.py`,
`tests/test_v024_public_verification.py`, `README.md`, `CHANGELOG.md`, `ROADMAP.md`, `SECURITY.md`,
`docs/README.md`, `docs/development-environment.md`, `docs/alpha/participant-quickstart.md`,
`docs/commercialization/design-partner-sprint.md`, `docs/releases/v0.2.3-status-and-next-stages.md`,
`docs/releases/v0.2.4-evaluation-candidate.md`, `site/index.html`, new
`docs/releases/v0.2.4-public-verification.md` and `.json`. Verify `uv.lock` without changing it
unless required; its editable dynamic-version project entry has no static version.

- [ ] Confirm clean isolated baseline and live release identity; baseline contracts pass.
- [ ] Update source-version and active-release contracts, observe expected pre-fix failures.
- [ ] Advance source identity, preserve both final-version guards, and align active documents.
- [ ] Create and strictly validate sanitized dated release evidence from retained records.
- [ ] Run focused contracts, locked checks, lint, whitespace and both deterministic benchmarks.
- [ ] Independent whole-branch review; resolve supported findings and rerun affected checks.
- [ ] Commit/push and create reviewable PR with accurate validation results.

### Task 2: Protected merge and closeout

- [ ] Verify exact-head full-suite/95% coverage, compatibility, packaging/browser and CodeQL checks.
- [ ] Merge only the reviewed passing expected head SHA; synchronize and verify resulting main.
- [ ] Verify public v0.2.4 tag/assets remain unchanged; record exact results and stop in maintenance.
