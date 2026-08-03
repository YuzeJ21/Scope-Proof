# ScopeProof Integrity and Reviewer-Loop Convergence Design

## Status

Approved by the project owner on 2026-08-03 through the instruction to implement every
non-Figma recommendation from the current-main product audit. This slice changes ingestion
integrity and reviewer workflow only. It does not publish a release or advance Stage 1.

## Goal

Prevent unavailable GitHub diff content from being treated as complete ingestion, then shorten
the path from a saved review or evidence-matrix finding to a current-head human decision without
weakening ScopeProof's deterministic evidence boundary.

## Product boundaries

- ScopeProof remains an evidence assistant, not a correctness oracle.
- Pull-request code is never executed.
- Missing repository data fails closed and can never be hidden by passing CI or human acceptance.
- Candidate evidence, external runtime evidence, criterion resolution, and final acceptance remain
  separate records.
- No paid API, LLM verdict, billing, account, private repository, generic code review, security
  scanning, automatic fix, comment, email, social post, or Figma dependency is added.
- Engineering tests and constructed demos contribute zero Stage 1 evidence.

## Selected approach

Use two independent, test-first changes on one branch:

1. Repair the GitHub ingestion boundary so every changed file is either represented by an
   inspectable text patch or exposed as an explicit partial-ingestion limitation.
2. Reuse the existing validated review, comparison, lifecycle, and export models to make re-review
   and criterion inspection direct. The Streamlit layer may orchestrate presentation and session
   state, but it must not reimplement core comparison, gate, or persistence logic.

Retrieval tuning, R-003 generation, CLI lifecycle parity, and evidence-adapter work remain separate
follow-on specifications so a regression in one subsystem cannot be disguised by another.

## GitHub patch-integrity contract

For every item returned by GitHub's pull-request files endpoint:

- a non-empty string `patch` is parsed under the existing per-file and total-size limits;
- an absent, `null`, or empty-string `patch` is not converted into an inspectable empty file;
- the unavailable path is excluded from `files`, included exactly once in `skipped_files`, and
  accompanied by one deterministic `Patch unavailable for <path>; file excluded from analysis.`
  warning;
- any unavailable patch makes `ingestion_state=partial`;
- a non-string patch is malformed adapter data and raises the existing bounded
  `GitHubIngestionError` rather than leaking a raw type error;
- available text patches in the same response remain analyzable;
- total-diff-limit copy is emitted only for files actually skipped by that limit.

The existing `Review` and `PullRequestSnapshot` Pydantic invariants remain the trusted boundary:
complete ingestion cannot contain warnings or skipped paths. Existing gate and final-acceptance
logic already reject partial ingestion; regression coverage must prove that path end to end.

## Saved-review current-head action

Opening a validated local review prepares its canonical public PR URL from the stored repository
and PR number. The primary fetch action is labelled `Check current head` for that reopened review.
One click uses the existing bounded `GitHubClient` fetch path and existing changed-head detection.

If the saved bundle contains unchanged-file candidate evidence, the workbench restores the unique
candidate paths into the advanced source option so a current-head comparison does not silently
drop that scope. Paths remain subject to the existing validation and fetch limits.

The action never carries prior decisions or final acceptance forward. Same-head reload still
requires current source confirmation and analysis. Changed-head reload preserves the old bundle as
the comparison base and displays the existing stale-evidence warning.

## Evidence matrix and decision navigation

Each matrix card adds:

- candidate count;
- one-line finding rationale;
- missing-evidence text when present;
- the deterministic recommended next action; and
- `Inspect this criterion`, which sets the existing criterion-detail selector and moves the
  reviewer to the detail workspace.

The default detail target is the first unresolved blocking criterion, then the first unresolved
criterion, then the first criterion in confirmed order. A user's explicit selection persists.
Changing targets continues to clear pending target-specific drafts through the existing guard and
shows the existing recovery notice.

## Contextual acceptance guard

When a reviewer selects `Accepted` while the observed evidence level is below the criterion's
required evidence level, the workbench must:

- label the state as acceptance despite insufficient candidate evidence;
- display required and observed levels before saving; and
- require a non-blank reviewer note.

This is a reviewer-attention guard, not a new verdict. It does not alter evidence levels, gate
precedence, or the meaning of accepted exceptions, change required, rejected finding, not in
scope, or atomically linked E3/E4 verification.

## Re-review comparison presentation

The workbench continues to compute comparison only through `compare_reviews()` and exposes:

- previous and current head SHA;
- all five deterministic change counts;
- changed candidates first;
- a collapsed `Unchanged candidates` section that renders the same immutable references and
  bounded limitation copy; and
- validated comparison Markdown and JSON downloads produced by the existing exporters.

Unchanged means the candidate reference did not change. It never means the criterion is correct or
accepted.

## Disclosure and field cleanup

- The constructed-demo disclosure appears only when the active review origin is
  `constructed_demo` or before any real review exists; it must not label a live public-PR review as
  a demo.
- Optional criteria source revision moves into a collapsed provenance detail without hiding the
  source reference or confirmer required for trustworthy confirmation.
- The local storage path moves out of the primary Start Review flow and remains visible inside the
  existing local-storage detail.

## Error handling

- Adapter failures use bounded existing error types and never expose credentials, local paths, or
  raw payloads.
- A failed current-head fetch leaves the reopened review unchanged and retryable.
- Direct criterion navigation cannot save or export pending drafts.
- Comparison export failure cannot mutate either review.
- UI helpers receive validated models and do not reinterpret core validation errors.

## Test strategy

Implementation follows strict RED-GREEN-REFACTOR cycles:

1. GitHub client tests for absent, null, empty, malformed, mixed available/unavailable, warning,
   skipped-path, and total-limit separation.
2. Gate/lifecycle projection proving partial ingestion cannot record final acceptance or Ready.
3. Streamlit tests for reopened URL and candidate-path preparation, one-click current-head fetch,
   matrix detail navigation, default blocking target, pending-draft clearing, acceptance-note guard,
   conditional demo disclosure, unchanged rendering, and comparison downloads.
4. Exporter regressions proving comparison bytes remain validated and deterministic.
5. Focused tests, Ruff, both constructed benchmarks, R-002 byte-integrity check, and the full suite
   with at least 95 percent product-code coverage.

## Success criteria

- No unavailable changed-file patch can appear as complete ingestion.
- Partial ingestion blocks final acceptance through existing deterministic gates.
- A reopened review can check the current head without retyping its PR URL or unchanged paths.
- Matrix findings lead directly to the correct criterion workspace with their actionable context.
- Insufficient-evidence acceptance requires an attributable explanation in the workbench.
- All five comparison classes are inspectable and Markdown/JSON comparison downloads are present.
- Live public-PR reviews are never labelled as the bundled constructed demo.
- Existing evidence IDs, retrieval thresholds, evidence levels, gate precedence, and saved review
  schemas remain unchanged.

## Self-review

- No placeholders or unresolved product choices remain in this slice.
- Ingestion behavior is defined at the adapter boundary and inherited by every consumer.
- UI changes reuse validated core state and existing comparison exporters.
- The scope is independent from R-003, retrieval tuning, CLI mutation commands, and evidence
  adapters, which will receive their own specifications after this branch is verified.
