# Resume reviewed source implementation plan

> **For agentic workers:** Use superpowers:executing-plans inline; independent test author and one fresh whole-branch review.

**Goal:** Continue a reopened saved review with matching ephemeral source without replacing its analysis.

**Architecture:** A pure core Pydantic receipt validates source facts and optimistic saved state. A separate UI action installs it; a session authority guard suppresses current conclusions/exports after contradictory observations.

**Tech Stack:** Python/Pydantic, Streamlit, pytest/AppTest, Playwright and protected GitHub CI.

**Spec:** `docs/superpowers/specs/2026-10-30-resume-reviewed-source-design.md`

## Global constraints

- Existing eight-file unchanged-source limit, exact full SHA/source/CI binding, complete ingestion only.
- Preserve confirmed criteria, attribution, decisions, gate semantics, producer metadata and record v6.
- Preserve frozen R-002, existing benchmarks, releases and Stage 3 gates; no source execution.
- No personal testing or qualifying reviews; routine choices delegated by the owner.

## Review focus

- Same-head fresh failed/different CI must not leave an authoritative Ready or live old export callback.
- Fetch-time storage mutation must reject attachment without writing or replacing either review.
- A legitimate reference/decision append must not invalidate unchanged source context.
- Unchanged files cited only by selected references must be restored within existing bounds.
- Origin/visibility must not turn constructed or unknown evidence into genuine-public claims.

### Task 1: Bound matching source and continued-use receipts

**Files:** new `scopeproof_core/reviews/source_attachment.py`, new `tests/reviews/test_source_attachment.py`.

**Interfaces:** See spec: `ReviewSourceAttachment`, `review_source_context_fingerprint`, `required_source_candidate_paths`, `prepare_saved_source_attachment`, `validate_source_attachment`. `SourceAttachmentUnavailable(ValueError)` exposes `observed_conflict: bool` for source-fact contradictions; optimistic storage conflicts have false.

- [ ] Independently write core RED regressions for exact matching, mismatches, candidates, CAS and neutral transitions.
- [ ] Implement validated receipt/source policy; no network inside storage lock and no persisted writes.
- [ ] Verify focused core/store/selected-reference tests, then commit as part of the reviewed slice.

### Task 2: Explicit source loading, authority conflict guard and browser continuation

**Files:** new `apps/web/source_attachment.py`, `apps/web/app.py`, `apps/web/deferred_exports.py`, new `tests/apps/test_source_attachment.py`, existing export/browser regressions.

**Interfaces:** UI module provides a persistent-per-session `SourceAuthorityGuard`, source-loading controls and receipt validation/reset helpers. `deferred_review_export` accepts optional `authority_check: Callable[[], bool]` and checks before/after rendering under existing storage validation.

- [ ] Observe UI RED for resumed state preservation, conflicts and stale queued exports.
- [ ] Add separate source action; preserve Check current head semantics and saved criteria/decisions.
- [ ] Restore unchanged candidate paths from both evidence collections. Bind attachment to context/source, clearing on hydrate/reset and invalidating on contradictions.
- [ ] Apply dedicated source conflict to current status, final acceptance, new exports and old callbacks without treating it as a storage conflict or a discardable draft.
- [ ] Extend installed-wheel constructed restart journey to save a second reference with unchanged analysis identity/gate/decisions and validate exports.

### Task 3: Evidence, roadmap and checked integration

**Files:** README, ROADMAP, release-status record and dated audit.

- [ ] Record this selected outcome, inspected alternatives and remaining genuine-use boundary accurately.
- [ ] Run focused/full 95%-coverage suite, lint/lock/diff, deterministic benchmarks and fresh browser/install proof; verify frozen-byte manifests.
- [ ] Obtain one fresh independent review, resolve supported findings and rerun affected checks.
- [ ] Prepare/attach PR, require exact reviewed-head CI/compatibility/CodeQL and clean findings, then guarded merge.
- [ ] Verify resulting main with fresh status reads, full-tree equality, frozen bytes and clean synchronized local checkouts; archive only owned ledger and report.
