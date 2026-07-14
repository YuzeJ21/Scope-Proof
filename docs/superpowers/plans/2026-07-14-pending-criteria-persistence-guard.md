# Pending Criteria Persistence Guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make unconfirmed criteria edits truthful unsaved work across replacement, local-save, export, and sidebar boundaries.

**Architecture:** Add one early presentation helper that compares current criterion widget state with authoritative criteria and one helper that restores authoritative widget values. Reuse the detector later in the editor, combine it with criterion-detail draft state for persistence readiness, and apply a rerun-safe discard marker without modifying persisted review objects.

**Tech Stack:** Python 3.12, Streamlit, Streamlit AppTest, pytest, Ruff.

## Global Constraints

- Users must still explicitly confirm normalized criteria before analysis.
- Discard must never revise criteria, invalidate analysis, mutate `ReviewState`, append an event, or alter the local-save fingerprint.
- Confirm must continue through `revise_criteria` and `confirm_criteria` and invalidate stale analysis.
- Persisted models, lifecycle services, deterministic gates, final acceptance, storage formats, and exporter contents remain unchanged.
- No paid APIs, LLMs, billing, forks, organizations, private repositories, synthetic validation, notifications, releases, or untrusted-code execution.

---

### Task 1: Guard persistence while criteria edits await confirmation

**Files:**
- Modify: `tests/apps/test_streamlit_app.py`
- Modify: `apps/web/app.py`
- Verify: `docs/superpowers/specs/2026-07-14-pending-criteria-persistence-guard-design.md`

**Interfaces:**
- Consumes: authoritative `list[Criterion]` plus `criterion_text_*`, `criterion_priority_*`, and `criterion_level_*` session keys.
- Produces: `_criteria_draft_pending(criteria: list[Criterion]) -> bool`, `_clear_criteria_draft(criteria: list[Criterion]) -> None`, and a combined pending-input Boolean for persistence controls.

- [ ] **Step 1: Write the failing persistence-boundary test**

Add `test_pending_criteria_edit_is_not_claimed_saved_or_exportable`. Save an
analyzed demo, change AC-01 text, priority, and evidence level, and require:

```python
assert "Saved locally — current review matches the last local save." not in captions
assert "Pending criteria edits are not saved or exported." in captions
assert app.button(key="save_review").disabled is True
assert all(button.disabled for button in app.download_button)
assert app.button(key="load_demo").disabled is True
assert app.button(key="discard_criteria_draft").disabled is False
assert "Pending — Resolve inputs before export" in sidebar
assert app.session_state["review_state"] == review_state
```

- [ ] **Step 2: Write the failing discard and confirm tests**

Add `test_discard_unconfirmed_criteria_edits_restores_saved_exportable_state` and
`test_confirmed_criteria_edit_becomes_authoritative_unsaved_review`. Require Discard
to restore all three widget values without review mutation, and require Confirm to
advance the revision, invalidate the old bundle, preserve explicit confirmation, and
enable analysis.

- [ ] **Step 3: Verify RED**

Run the three new tests. Expected: the persistence test fails on the saved-match claim,
enabled downloads, unprotected replacement, and missing sidebar state; the discard
test cannot find `discard_criteria_draft`; the confirm contract remains a control.

- [ ] **Step 4: Implement the early detector and rerun-safe discard**

Add helpers equivalent to:

```python
def _criteria_draft_pending(criteria: list[Criterion]) -> bool:
    return any(
        not str(st.session_state.get(f"criterion_text_{item.criterion_id}", item.text)).strip()
        or st.session_state.get(f"criterion_text_{item.criterion_id}", item.text) != item.text
        or st.session_state.get(f"criterion_priority_{item.criterion_id}", item.priority)
        != item.priority
        or st.session_state.get(
            f"criterion_level_{item.criterion_id}", item.required_evidence_level
        )
        != item.required_evidence_level
        for item in criteria
    )


def _clear_criteria_draft(criteria: list[Criterion]) -> None:
    for item in criteria:
        st.session_state[f"criterion_text_{item.criterion_id}"] = item.text
        st.session_state[f"criterion_priority_{item.criterion_id}"] = item.priority
        st.session_state[f"criterion_level_{item.criterion_id}"] = (
            item.required_evidence_level
        )
```

Consume `criteria_draft_reset_pending` before global unsaved-state derivation. After
the criteria widgets render, show `Discard unconfirmed criteria edits`; on click set
the reset marker and success notice, then rerun.

- [ ] **Step 5: Apply one combined persistence boundary**

Derive:

```python
has_pending_criteria_draft = _criteria_draft_pending(st.session_state["criteria"])
has_pending_review_input = (
    has_pending_criteria_draft or has_pending_criterion_detail_draft
)
```

Use `has_pending_review_input` for replacement protection, saved-match readiness,
local-save disabled state, download disabled state, and unavailable-storage guidance.
Use the criteria-specific Boolean for exact summary guidance. Reuse
`_criteria_draft_pending(criteria)` for later `criteria_edits_pending`. Render sidebar
text `Pending — Resolve inputs before export` whenever analysis exists and either
pending-input Boolean is true.

- [ ] **Step 6: Verify GREEN and adjacent behavior**

Run the three new tests plus blank-edit, pending-text-edit, unchanged-confirmation,
criterion-detail-draft, local-save, save/reopen, and sidebar-navigation regressions.
Then run:

```bash
"/Users/yjian070/Documents/New project 2/.venv/bin/ruff" check \
  apps/web/app.py tests/apps/test_streamlit_app.py
git diff --check
```

- [ ] **Step 7: Run complete product verification**

Run repository-wide Ruff, complete offline pytest, `scopeproof benchmark`, and a
loopback Streamlit health check. Require all tests passing apart from the intentional
live skip, 12 benchmark cases, 13 criteria, zero mismatches, zero must-have False
Ready, zero false blockers, exact health `ok`, and no traceback.

- [ ] **Step 8: Commit and integrate**

Stage exactly the app, AppTests, design, and plan. Commit the implementation, push
`codex/pending-criteria-persistence-guard`, open one ready protected PR, require both
`verify` checks plus CodeQL, merge only at the reviewed head SHA, synchronize local
main, and require exact-main CI and CodeQL success. Do not create a release, issue
comment, label, reviewer request, or other notification.
