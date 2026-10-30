# Reviewer-selected exact-head references

## Intent and scope

M3 lets a reviewer explicitly cite an inspectable source line omitted by conservative matching.
The owner authorizes implementation, automated testing, independent review and checked merge,
and delegates routine design decisions. This design is the implementer's bounded choice.

Selected references are a separate, non-gating static collection, not automatic candidates.
Appending one must preserve findings, retrieval diagnostics, gate, scope decisions, resolutions,
runtime/JUnit records, final acceptance and prior analyses. It neither resolves an uncited file
nor proves a criterion satisfied. A test/eval definition is E2 intent, never executed verification.

## Approaches considered

1. Add selected lines to automatic candidates: mixes manual relevance with algorithm scores and
   changes diagnostic counts, confidence and gates. Rejected for this slice.
2. Store full source catalogs: supports adding after reopen without loading source, but expands
   storage, migration and source-retention scope. Deferred.
3. Persist attributable selected references only: chosen. Selection uses current ingested source;
   saved references survive reopening for display/export. Adding after reopen requires loaded
   matching source. No extra fetching, execution or automatic acceptance occurs.

## Core contract

New `scopeproof_core/reviews/selected_references.py` provides:

- `selectable_reference_lines(state, snapshot, unchanged_files=None)` returns strict frozen
  `SelectableReferenceLine` values with source_scope, file_path, line_number, excerpt,
  evidence_type and evidence_level. It validates confirmed active analysis and exact repository,
  PR, base/head and changed-file inventory. Sources are already-ingested current-head added or
  context lines, or exact-head unchanged-file content. Removed/deleted, skipped, truncated,
  ambiguous, missing and noncanonical paths are unavailable. Whitespace-only/oversized lines
  are unavailable. Renames use their current path. Generated inspectable lines remain static.
- Limits: first 1,000 eligible lines in deterministic scope/path/line order, maximum 4,096 UTF-8
  bytes per line, at most 32 saved references per active analysis. UI states the bounded limit.
- `append_reviewer_selected_reference(state, *, snapshot, selected, criterion_id, reviewer,
  rationale, expected_state_fingerprint, unchanged_files=None)` revalidates mutable inputs,
  compares the complete state fingerprint and exact selected value against newly derived source
  lines, constructs source fields itself and returns a revalidated new state. Reject duplicates
  for the same criterion/source/path/line, invalid criterion, blank attribution/rationale,
  unknown inventory, unconfirmed analysis and final acceptance (revoke first).
- `reviewer_selected_references` is a default-empty `ReviewBundle` collection of frozen,
  extra-forbid `ReviewerSelectedReference` models. Each carries reference_id, review_id,
  repository, pr_number, head_sha, criteria_revision_number, confirmed_criteria_sha256,
  criteria_source_provenance, criterion_id, source_scope, file_path, line_number, excerpt,
  excerpt_sha256, derived evidence_type/E1-or-E2, immutable permalink, reviewer, rationale and
  selected_at. Attribution and rationale are bounded (200/2,000 characters). Validate digest,
  type/level, location, exact ownership, confirmed provenance, unique IDs and duplicate locations.
  A stored digest establishes internal consistency, not independent source authenticity.

## Persistence and export

Advance saved record version 5 to 6; read versions 1–6. Before legacy migration, reject any
nonempty or malformed selected-reference field in pre-6 active/history bundles. Missing/[] means
no recorded selections; never invent attribution. Preserve all existing CI/runtime migrations
and the unknown changed-file inventory rule for versions below 5. Existing files are not rewritten
by load. JSON includes typed references; Markdown/HTML and per-criterion CSV explicitly include
attribution, exact source identity and the non-gating/test-intent boundary. Comparison projections
continue comparing automatic candidates/scope only and state that selected references are excluded.

## Workbench

Show saved references separately from automatic candidates in Criterion Review. Provide an
explicit source then numbered-line selector (both initially empty), preview, required rationale,
attributable reviewer and save action. Derive level/type; no pasted excerpt/URL/level.
Bind selection drafts to review/head/revision/criterion and source context. Any selection/rationale
is a pending criterion input and blocks exports, autosave and acceptance until saved/cleared.
Target changes clear drafts; failed transitions retain them. Success clears only consumed inputs.
Use existing optimistic persistence/conflict handling; do not overwrite newer records.

## Verification and boundaries

RED→GREEN tests cover identity/provenance, omitted lines, changed/renamed/unchanged/test/generated
sources, invalid/removed/skipped/truncated/ambiguous lines, limits, duplicate/stale requests,
unchanged gating/decisions/history, legacy migration, exports, draft/reset/conflict handling and
installed-wheel select/save/restart/reopen/download. Constructed sources/actors stay labelled.
Run the full 95% covered suite, lint, deterministic benchmarks, installed-wheel/browser and
available Python/Windows compatibility; independent review; exact-head CI guarded merge; main
verification. No dependency/retrieval/frozen R-002 change, release, deployment, participant contact,
generic review/scanning/autofix, target execution, human validation or Stage 3 advancement.
