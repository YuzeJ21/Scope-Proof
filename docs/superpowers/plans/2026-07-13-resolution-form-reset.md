# Resolution Form Reset Implementation Plan

> **For agentic workers:** Follow test-driven development and verification-before-completion for
> each task. This plan is intentionally a single small UI-state slice.

**Goal:** Make every new human resolution a deliberate action by clearing the resolution controls
after a successful append while preserving the success confirmation and audit history.

**Architecture:** Keep event semantics in the existing core. Add only ephemeral Streamlit session
state for a post-save reset marker and one-run success notice, consumed before keyed widgets render.

**Tech Stack:** Python 3.11+, Streamlit, Streamlit AppTest, pytest, Ruff.

## Global Constraints

- Do not change gate evaluation, evidence levels, resolution replacement, or history semantics.
- Do not clear inputs when validation or append fails.
- Do not introduce a persisted or exported object.
- Keep the core independent from Streamlit.
- Add regression coverage before production implementation.

---

### Task 1: Specify post-save form behavior

**Files:**
- Test: `tests/apps/test_streamlit_app.py`

- [ ] Add an AppTest that loads the demo, confirms criteria, runs analysis, selects AC-01 Accepted,
  enters a reviewer note, and saves the resolution.
- [ ] Assert exactly one resolution event, an empty decision, an empty note, a disabled save button,
  and the existing success message.
- [ ] Run only the new test and require RED because the current widgets retain their values.

### Task 2: Implement the minimal reset lifecycle

**Files:**
- Modify: `apps/web/app.py`

- [ ] Before rendering the resolution widgets, consume a pending reset marker and clear the three
  resolution-widget keys.
- [ ] Consume and display a pending success notice in the same section.
- [ ] After a successful append, set the reset marker and notice, then rerun.
- [ ] Run the new test, the complete Streamlit AppTest file, and Ruff on changed Python files.

### Task 3: Verify and publish

- [ ] Run `ruff check .`, the complete pytest suite, `git diff --check`, and inspect the diff.
- [ ] Run all 12 deterministic benchmark cases and require zero must-have False Ready, zero False
  Blocker, and zero mismatches.
- [ ] Build and install the wheel in a clean environment; verify installed CLI benchmark and web
  health.
- [ ] Repeat the demo in the live browser and confirm the post-save form is empty and disabled,
  the success notice is visible, history has one current event, and the gate remains Blocked.
- [ ] Push `codex/resolution-form-reset`, open one meaningful ready PR, wait for all required checks,
  merge only when green, verify exact post-merge main CI, and synchronize local `main`.
