# ScopeProof Workbench UX Simplification Design

## Status

Approved product direction: Approach 2, a bounded redesign of the existing Streamlit workbench.
This specification records the approved direction before implementation planning. It does not
authorize a release, change the evidence engine, or claim genuine-user validation.

## Repository baseline

- Implementation starts from public `main` at merge commit
  `f4d5da8353087541f3b16e32e25ba2b4add7f6d6`.
- The isolated branch is `codex/workbench-ux-simplification`.
- The locked development environment passes `1634` tests with `1` intentional skip.
- The stale root checkout and its untracked `.coverage 2` file are outside this work.
- Source version remains `0.2.3`; publishing a tag or GitHub Release is a separate owner gate.

## Problem

The deterministic review engine and its fail-closed boundaries are working, but the current
workbench makes a first review feel slower and more complicated than it is. Seven related
presentation and workflow problems remain:

1. The real public-PR input appears after optional alpha and demo controls.
2. A long criteria list pushes the confirmation action below the visible area.
3. CI diagnostics dominate the evidence-matrix entry point.
4. Candidate evidence and the ordinary reviewer decision are separated by a long form.
5. Evidence-heavy criteria produce many repeated item-level expanders.
6. Optional E3/E4 external verification appears before the ordinary reviewer decision.
7. Review status and exports appear after manual-save and optional alpha-feedback controls.

The current app already collapses individual evidence items and already permits export without a
local save when no draft is pending. The remaining work is therefore grouping, placement, safe
autosave, and clearer hierarchy—not a new evidence workflow.

## Goals

1. Put a genuine public PR review ahead of demo, research, and advanced controls.
2. Keep explicit criteria confirmation visible without weakening confirmation or draft guards.
3. Preserve the complete CI observation while reducing first-screen density.
4. Present the selected criterion's evidence and ordinary decision as one coherent workspace.
5. Group repeated evidence affordances without changing evidence identity, rank, or content.
6. Make E3/E4 recording clearly optional and keep its existing atomic evidence-plus-resolution
   behavior.
7. Surface the deterministic gate status and available exports immediately.
8. Autosave only validated, authoritative review state and retain an explicit recovery path.
9. Improve desktop, narrow-screen, keyboard-focus, and zoom usability where locally verifiable.

## Non-goals and evidence boundaries

- No evidence schema, evidence level, retrieval rule, gate threshold, or verdict change.
- No generic code review, security scanning, semantic model, auto-fix, or target-code execution.
- No paid LLM/API, billing, account system, private repository, or persisted GitHub token.
- No raw rendering of repository-controlled text as HTML or Markdown.
- No conversion of engineering tests, constructed demos, R-002/R-003 research, or owner rehearsal
  into Stage 1, customer, market, runtime-correctness, or repeat-use evidence.
- No claim of screen-reader, Windows, Linux, or WCAG validation without matching evidence.
- No tag, Release, merge, push, public comment, email, DM, or social post as part of this design.

## Considered approaches

### 1. Reorder and collapse only

Move a few controls and add expanders without changing save behavior or the selected-criterion
layout. This is lower risk but leaves evidence, decisions, and exports fragmented. Rejected because
it does not resolve the approved scope.

### 2. Bounded workbench redesign — selected

Restructure the existing five-stage Streamlit workbench in three tested slices: entry and criteria,
evidence and decisions, then status/export/autosave. Keep every authoritative operation in the
existing lifecycle, storage, export, and gate services. This resolves the seven presentation issues
without changing the core engine.

### 3. New wizard or frontend rewrite

Replace the current workbench with a new multi-page wizard or a different frontend framework. This
would create duplicate state transitions, migration work, and evidence-boundary risk. Rejected for
this product stage.

## Experience design

### 1. Start Review

The first active surface under the product boundary statement contains:

- the `Public GitHub pull request URL` input;
- its neutral validation message; and
- the full-width `Fetch public PR` action.

The URL remains a canonical public GitHub PR URL and fetch enablement retains all existing
replacement and alpha-qualification guards. Reserve the Fetch action with `st.empty()` so it can
appear directly below the URL while its handler is populated only after the optional qualification
state has been evaluated. Optional controls move below the primary entry:

- `Try ScopeProof` contains the deliberately constructed demo action;
- `Alpha feedback session` contains the research qualification fields and remains off by default;
- `Advanced source options` contains the session-only token and bounded unchanged paths; and
- `Resume a saved review` contains local reopen and delete controls.

These controls must not look required for a standard review. The token remains session-only and is
never saved or exported. The demo remains visibly labelled constructed evidence.

### 2. Confirm Criteria

Render a compact top summary showing the number of criteria, validation state, confirmation state,
and whether edits are pending. Reserve a top action location with `st.empty()` and populate it after
all editable widgets have been evaluated, so one `Confirm criteria` button appears before the long
list while retaining correct enablement.

Each criterion uses one default-collapsed editor labelled with:

- criterion ID;
- priority; and
- required evidence level.

The full criterion text appears immediately inside the editor using an inert Streamlit text widget,
followed by the text input, priority selector, evidence-level selector, remove action, and move
action. Repository-controlled text does not enter the expander's Markdown-capable label and is
never rendered as raw HTML. Add and split controls move into an `Add or split criteria` expander.
Blank-text and validation warnings appear next to the top summary and the matching editor.

Confirmation still calls the existing `revise_criteria()` and `confirm_criteria()` lifecycle. Any
edit, add, split, removal, or reorder still invalidates prior analysis. Pending inputs remain
excluded from save and export until submitted, confirmed, discarded, or cleared.

### 3. Evidence Matrix entry

Replace the large repeated CI block with a compact observation summary containing:

- observed CI state;
- the complete- or partial-collection state;
- total, passing, pending, failing, neutral, and skipped counts; and
- runtime-verification state.

The deterministic CI reason remains visible. Failing, pending, partial, neutral-only, skipped, or
otherwise limiting observations receive visible warning copy rather than being hidden. Exact check
names, collection diagnostics, research-boundary details, and the longer static-versus-runtime
explanation move into `CI details and evidence boundary`.

The loaded-source identity should no longer repeat the full CI diagnostic. It retains repository,
PR number, immutable head SHA, changed-file count, and ingestion state. Partial-ingestion warnings
remain prominent because they affect the gate.

### 4. Selected criterion workspace

On wide screens, render the selected criterion in two responsive columns:

- **Evidence and search**: evidence status, finding explanation, missing evidence, recommended next
  action, search diagnostics, and grouped candidate evidence.
- **Reviewer decision**: current resolution, attributable reviewer, ordinary human decision,
  reviewer note, deterministic decision impact, and save action.

Streamlit's responsive stacking provides a narrow-screen fallback. Evidence appears before the
decision when stacked, so the reviewer still reads the basis before deciding. The criterion ID and
full inert criterion text appear once above both columns.

The ordinary resolution continues to call `append_resolution()`. It never records final review
acceptance and never creates runtime evidence.

### 5. Candidate evidence grouping

Group linked evidence by `(file_path, evidence_type)` in deterministic first-occurrence order. Each
group receives one default-collapsed expander labelled with a group number, evidence type, and item
count. The repository-controlled path appears inside through `st.code`, not in the expander's
Markdown-capable label. Render every existing item in rank order with its immutable line range,
evidence level, excerpt, bounded context, permalink, matching rationale, rule, and limitations.

Grouping is a view operation only. It must not deduplicate, rerank, truncate, merge, or rewrite
evidence items. Test definitions continue to say that they show intent rather than executed
verification.

### 6. Optional external verification

Place `Record optional external verification (E3/E4)` after the ordinary resolution in the reviewer
column. It is default-collapsed and states before expansion that ScopeProof does not run PR code or
infer runtime results.

After expansion, retain all required fields, evidence-level choices, validation, and the existing
single `append_external_verification()` operation. Saving must continue to append the runtime
evidence and its `MANUALLY_VERIFIED` resolution atomically. E4 remains a claimed evidence level on
that event; it does not record final review acceptance.

Existing runtime records remain visible in a separate compact history below the optional form.

### 7. Summary, export, and local persistence

The first content under `Summary & Export` is:

1. deterministic review status;
2. gate reason codes and next actions;
3. immutable head SHA and ruleset; and
4. Markdown, JSON, and CSV download actions.

Exports continue to derive from the validated `ReviewState` when available and otherwise the
validated `ReviewBundle`. They remain disabled whenever any criteria, authoring, requirements, or
criterion-detail draft is pending. Local save is not an export prerequisite.

The review ID, autosave state, local-storage warning, explicit save/retry action, and saved-review
management move into `Local review storage`. Optional alpha feedback follows the primary status and
exports and retains its consent and qualification boundaries.

## Safe autosave design

Autosave runs only when all of the following are true:

1. a validated `ReviewState` exists;
2. no pending review input exists;
3. the local `JsonReviewStore` is available;
4. the current deterministic review fingerprint differs from the last successful save; and
5. the same fingerprint has not already failed or been explicitly deleted during the current
   session.

The app calls the existing `JsonReviewStore.save(review_state)`. That store validates the complete
state at its trusted boundary, serializes the validated Pydantic model, writes through a temporary
file, and atomically replaces the target. No widget draft is copied into `ReviewState`, so autosave
can never persist unconfirmed text.

Attempt autosave before deriving the displayed saved-state and alpha-outcome enablement, so the
current run consistently observes a successful save. On success, record the fingerprint and show a
compact `Saved automatically` state. Do not force an extra rerun. On `OSError` or `ValueError`,
retain the open review, record the failed fingerprint to avoid a write loop, and show one explicit
`Retry local save` action. A later authoritative state gets a new fingerprint and may autosave
normally. If the store is unsafe or unavailable, skip the write and retain the current warning and
exports when no draft is pending.

Keep the existing `save_review` widget key in the local-storage expander for compatibility and
explicit recovery. Its label may become `Save now` or `Retry local save`; it remains disabled when
the current authoritative state already matches the successful local save or when drafts make the
state ineligible.

Reopened reviews set the successful fingerprint during hydration, so merely viewing an unchanged
review does not rewrite it. Deleting the saved record for the currently open review keeps the
in-memory review as unsaved work and suppresses autosave for that exact fingerprint; otherwise the
next rerun would silently recreate the deleted file. An explicit save clears that suppression. A
later authoritative mutation produces a new fingerprint and may autosave normally. Deleting a
different saved review does not suppress autosave for the current review.

## Visual and accessibility behavior

- Use Streamlit's built-in bordered containers, columns, spacing, and expanders rather than brittle
  DOM selectors or a new component framework.
- Keep one primary action per stage and reduce repeated explanatory paragraphs.
- Retain the existing high-contrast `:focus-visible` treatment.
- Do not implement a CSS-sticky confirmation action; the placeholder keeps it early in document
  and keyboard order without overlay risk.
- Keep labels visible and attributable; placeholders never replace required labels.
- Verify desktop and narrow viewports, keyboard-only operation for the changed path, and 200% zoom
  where the local browser permits it.
- Record screen-reader and unavailable operating-system coverage as open evidence, not passed QA.

## Error handling

- Invalid PR URLs retain neutral, actionable guidance and never trigger a request.
- Fetch, criteria, resolution, runtime-evidence, storage, and export failures retain the current
  authoritative review and use the existing fail-closed behavior.
- A presentation helper must not catch or reinterpret core lifecycle validation errors.
- Autosave failures must not disable valid exports or repeatedly write on every Streamlit rerun.
- Grouping or compact rendering must tolerate zero evidence, historical reviews without retrieval
  diagnostics, and partial ingestion.

## Architecture and expected files

The core engine remains independent from Streamlit. The primary implementation stays in:

- `apps/web/app.py` for layout, local view grouping, and autosave orchestration;
- `tests/apps/test_streamlit_app.py` for state, ordering, draft, autosave, and rendering contracts;
- focused browser evidence and release-audit documentation for current-run verification.

If a pure helper is needed for deterministic evidence grouping or compact labels, place it in the
web layer and test it there. Do not move persistence, lifecycle, gate, retrieval, or export logic
into the UI, and do not change a core schema for presentation state.

## Test strategy

Implementation uses test-driven development and three bounded slices.

### Slice A — entry and criteria

Add failing AppTest/source-order coverage for:

- PR URL and Fetch before optional demo, alpha, advanced, and reopen controls;
- standard review usable without opening optional controls;
- one early criteria-confirmation action;
- default-collapsed criterion editors with complete edit controls;
- unchanged confirmation, invalidation, draft-discard, add, split, remove, and reorder semantics.

Verify the focused tests fail before the layout change and pass afterward.

### Slice B — evidence and decisions

Add failing coverage for:

- one compact CI summary plus a details expander, with all limiting states still visible;
- no duplicated verbose CI block in loaded-source identity;
- selected evidence and ordinary resolution in one workspace;
- ordinary resolution before the optional E3/E4 form;
- deterministic grouping that renders every evidence ID once and preserves order/content;
- unchanged `append_resolution()` and atomic `append_external_verification()` behavior.

### Slice C — summary, export, and autosave

Add failing coverage for:

- status and three downloads before local-storage and alpha-feedback controls;
- downloads available without a manual save when no draft is pending;
- downloads disabled for every pending-draft category;
- autosave success, no-op for an unchanged fingerprint, and new save after authoritative mutation;
- no autosave for pending drafts or unavailable storage;
- one-attempt behavior and explicit retry after a save failure;
- reopen no-rewrite behavior, current-review delete suppression, unrelated-review deletion,
  alpha-outcome enablement, and manual-save compatibility.

### Completion verification

Run, in order:

1. focused RED/GREEN tests for each slice;
2. `uv run pytest tests/apps/test_streamlit_app.py -q`;
3. `uv run ruff check .`;
4. `uv run pytest -q` with the locked development environment;
5. lock/install and package smoke checks used by the current release-readiness workflow;
6. fresh pointer-flow checks at desktop and narrow viewport;
7. keyboard-only checks for PR entry, criteria confirmation, criterion selection, resolution,
   optional verification, and export;
8. 200% zoom inspection if locally controllable; and
9. diff hygiene proving no generated benchmark, coverage, local-review, or research artifact was
   committed.

## Success criteria

- A standard public PR URL and Fetch action are the first review controls.
- A reviewer can confirm a long criteria set without scrolling to its end.
- CI limitations remain truthful but no longer dominate the matrix entry point.
- Evidence and the ordinary human decision are available in one selected-criterion workspace.
- Optional E3/E4 recording follows the ordinary decision and remains visibly optional.
- Every linked evidence item remains inspectable exactly once under deterministic grouping.
- Gate status and valid exports are immediately available; drafts still fail closed.
- Valid authoritative review changes save automatically without persisting drafts or looping after
  failure.
- All existing evidence, lifecycle, persistence, export, and gate regressions pass.
- Browser evidence supports only the environments and interactions actually exercised.
- Stage 1 and release status remain unchanged unless separate genuine evidence and owner approval
  are obtained.
