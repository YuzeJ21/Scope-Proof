# ScopeProof Runtime-Evidence Form Reset Design

## Problem

The manual runtime-evidence prerequisite defect described in the continuation objective has already
been fixed on `main`: empty or whitespace-only required values keep the save control disabled,
complete values enable it, and unexpected Pydantic failures use product-facing recovery copy.
Current live-browser evidence confirms that behavior.

A related first-use defect remains after a successful append. The artifact reference, scenario,
environment, observed result, reviewer, limitations, and evidence level remain in Streamlit widget
state. The save control therefore remains enabled, and an immediate second click appends the same
record again. A deterministic AppTest probe reproduces this with one appended record, every input
still populated, and `save_runtime_evidence.disabled == False`.

This is a presentation-state defect. `RuntimeEvidence` validation, append-only lifecycle behavior,
static findings, gate evaluation, and final acceptance are working as designed.

## Chosen Design

After `append_runtime_evidence` succeeds, set a pending reset marker and a one-run success notice in
Streamlit session state, then call `st.rerun()`. Before rendering the runtime-evidence widgets on
the next run, consume the marker and reset all runtime-evidence widget keys to their initial state:

- required text fields become empty;
- optional limitations become empty;
- evidence level returns to the existing E3 default.

Consume and display the saved success notice after the widgets. Because readiness is derived from
the cleared required values, the save control becomes disabled automatically. The recorded runtime
evidence remains visible beneath the form as the durable confirmation of what was appended.

This mirrors the existing human-resolution form reset pattern and keeps all new behavior in the
Streamlit presentation layer.

## Alternatives Considered

1. **Use the existing pending-reset and rerun pattern — chosen.** This is the smallest change,
   matches an established workbench pattern, preserves the success message, and prevents accidental
   repeat submission without altering append semantics.
2. **Convert the section to `st.form(clear_on_submit=True)`.** Streamlit could clear the fields, but
   this changes how readiness updates and restructures a working section for no additional product
   value.
3. **Deduplicate in `append_runtime_evidence`.** Identical observations may legitimately be recorded
   at different times or by different reviewers. Core deduplication would change evidence semantics
   and hide intent instead of fixing stale UI state.

## Components and Data Flow

- `apps/web/app.py` owns the pending reset marker, notice, widget reset, rerun, and presentation.
- `RuntimeEvidence` remains the authoritative validator for any persisted record.
- `append_runtime_evidence(ReviewState, RuntimeEvidence) -> ReviewState` remains unchanged and
  append-only.
- Existing selected-criterion behavior remains unchanged; the appended record is rendered for the
  criterion selected at submission time.
- Resolution events, final acceptance, gate evaluation, exports, and storage remain unchanged.

## Error and Safety Behavior

- Failed validation or append attempts do not set the reset marker, clear the form, or rerun.
- Only a successful append clears the form.
- The success notice survives exactly the rerun required to clear widget state.
- Cleared required values deterministically disable the save control.
- No PR code runs, no runtime result is inferred, and no static finding or gate is upgraded.
- Test fixtures demonstrate UI behavior only and are never represented as genuine runtime evidence.

## UX and Accessibility Notes

The existing prerequisite state is healthy: labels are explicit, required-field guidance is visible,
and the disabled control prevents an invalid first action. The remaining risk is state-change clarity
after success. Clearing the fields, retaining a visible success status, disabling the action, and
showing the appended record provide four consistent signals that submission completed. Screenshot
inspection can verify visible state and copy; keyboard focus behavior and assistive-technology
announcement quality still require runtime interaction checks and cannot be claimed from images alone.

## Verification

- Add a failing Streamlit AppTest that submits one complete fixture record and proves the current
  form remains populated and enabled.
- Change the expected contract so the form is empty, E3 is selected, Save is disabled, the success
  notice is visible, and exactly one runtime record exists.
- Preserve the existing prerequisite, schema, lifecycle, final-acceptance, and unchanged-static-
  finding tests.
- Run focused AppTests, Ruff, the full offline suite, the deterministic benchmark, `git diff --check`,
  a clean-installed wheel benchmark and health smoke, and a live-browser check of the cleared form.
- In live-browser verification, use explicitly labeled non-evidence form values and do not submit
  them. Use AppTest fixtures—not external-evidence claims—to exercise the successful-save transition.

## Out of Scope

- Runtime-evidence schema or evidence-level changes.
- Core deduplication or idempotency semantics.
- Gate, finding, resolution, final-acceptance, export, or persistence changes.
- Release publication; this is an unreleased workbench reliability improvement.
- Paid services, APIs, telemetry, fork testing, synthetic product validation, or external claims.
