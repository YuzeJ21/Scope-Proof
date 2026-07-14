# Pending Criteria Confirmation Design

## Problem

A clean-installed `0.1.16.dev0` browser audit reproduced a trust gap after deterministic
analysis. Editing a criterion widget changes the visible requirement, priority, or required
evidence level, but the authoritative `st.session_state["criteria"]`, current analysis bundle,
evidence matrix, and criterion detail continue to use the last confirmed criteria until the
reviewer presses `Confirm criteria`.

In the reproduced AC-01 case, the editor displayed `Changed visible criterion` while the evidence
matrix and criterion detail still displayed `User can export the research list as CSV`. At the same
time, the sidebar continued to say `Complete — Criteria confirmed`, the analysis button remained
enabled, and no message explained which criterion set controlled the results. The engine still used
the confirmed set, so this is a presentation/readiness defect rather than an evidence, lifecycle,
or gate defect.

## Decision

Derive a transient `criteria_edits_pending` Boolean by comparing the rendered `edited_criteria`
with the authoritative criteria list. This value remains session-only and is not persisted or
exported.

When edits are pending:

- show a warning beside the confirmation controls that the visible edits are not yet confirmed;
- state that any visible evidence and verdict still use the last confirmed criteria;
- disable `Run deterministic analysis` until the reviewer confirms the updated set;
- report `Next — Confirm updated criteria` in the sidebar instead of claiming that criteria are
  complete;
- keep the prior analysis visible so an accidental edit does not destroy review work.

On `Confirm criteria`, preserve the existing lifecycle path. For an analyzed review,
`revise_criteria` archives the prior bundle, creates an unconfirmed revision, and clears active
analysis; `confirm_criteria` then confirms that revision. The reviewer must rerun analysis before
new results are available. Set the transient pending flag false in the same Streamlit run so the
confirmation message and sidebar immediately reflect the newly confirmed state.

## Alternatives Considered

1. **Pending-state guidance and analysis lock — selected.** It makes the controlling criterion set
   explicit without discarding valid prior analysis or adding durable state.
2. **Automatically invalidate analysis on every widget change.** This is stricter, but an accidental
   keystroke would immediately archive the current analysis and create avoidable data-loss risk.
3. **Lock criteria after analysis behind an explicit edit mode.** This prevents accidental edits,
   but introduces a new mode, control, and state transition for a problem that a derived readiness
   rule can solve more simply.

## Components and Data Flow

- `apps/web/app.py` derives `criteria_edits_pending` only from validated `Criterion` objects already
  produced by the editor.
- The confirmation handler remains the only place that copies edited criteria into authoritative
  session and lifecycle state.
- `_analyze`, `ReviewState`, `CriteriaRevision`, retrieval, findings, gates, persistence, and exports
  remain unchanged.
- The sidebar consumes the derived flag only to distinguish confirmed criteria from visible pending
  edits.

## Error and Safety Behavior

- Blank criterion text continues to disable confirmation through the existing validation rule.
- Pending edits cannot be analyzed before explicit confirmation.
- Existing analysis remains visibly available but is labeled as belonging to the last confirmed
  criteria.
- No evidence is inferred, upgraded, or reclassified, and no untrusted repository code executes.
- No persisted or exported schema changes are introduced.

## Verification

- Add an AppTest that analyzes the demo, edits AC-01, and proves:
  - the visible widget differs from the authoritative and bundle criteria;
  - the pending warning names the last-confirmed-results boundary;
  - analysis is disabled;
  - the sidebar says `Next — Confirm updated criteria` and does not claim criteria are complete.
- Confirm the edit and prove the updated criterion becomes authoritative, criteria stay explicitly
  confirmed, active analysis is cleared, and the sidebar points to deterministic analysis next.
- Cover priority or required-evidence-level edits through the same derived comparison contract.
- Run focused AppTests, Ruff, the complete offline suite, deterministic benchmark, diff checks, a
  clean wheel install, exact health check, and packaged browser before/after verification.

## Out of Scope

- Automatically applying widget edits without confirmation.
- Hiding or deleting the last confirmed analysis while edits are pending.
- Changing criteria revision history, evidence retrieval, findings, gate evaluation, final
  acceptance, runtime evidence, storage, or exports.
- Adding CSS, JavaScript, dependencies, APIs, telemetry, billing, or notification-generating work.
