# Lifecycle State Revalidation Implementation Plan

> **For agentic workers:** Use `superpowers:executing-plans` to implement each checked task with
> test-first evidence and verification before publication.

**Goal:** Reject validator-bypassed `ReviewState` objects consistently at every public lifecycle
mutation boundary.

**Architecture:** Add one private lifecycle helper that reconstructs `ReviewState` from its complete
Python dump, then call it before every public state-changing operation reads or mutates state.

**Tech stack:** Python 3.12, Pydantic v2, pytest, Ruff.

## Constraints

- Preserve deterministic gates and treat False Ready as more harmful than False Blocked.
- Reject contradictory state; never normalize, auto-repair, or invent audit identity.
- Keep the core independent from Streamlit and GitHub UI layers.
- No billing, paid APIs, LLM APIs, organizations, second accounts, private repositories, forks,
  untrusted code execution, synthetic validation, comments, or release.

### Task 1: Lock the boundary defect with tests

**Files:**
- Modify: `tests/reviews/test_lifecycle.py`

- [ ] Build one valid state, use `model_copy(...)` to change only the top-level head SHA, and prove
  `revise_criteria`, `confirm_criteria`, `append_resolution`, and `append_runtime_evidence` each
  reject it with the active-review identity error.
- [ ] Run the focused tests and capture RED behavior: revise and resolution currently normalize,
  runtime evidence propagates, and confirmation reports only its later transition precondition.

### Task 2: Revalidate lifecycle inputs

**Files:**
- Modify: `scopeproof_core/reviews/lifecycle.py`
- Test: `tests/reviews/test_lifecycle.py`

- [ ] Add `_validated_state(state)` using complete dump-and-revalidate semantics.
- [ ] Rebind state through the helper at the beginning of all four public state mutation functions.
- [ ] Run focused lifecycle tests and Ruff; require all tests green.

### Task 3: Full verification and protected publication

- [ ] Run Ruff, the complete offline test suite, the deterministic benchmark, and
  `git diff --check`.
- [ ] Build and install a clean wheel in `/tmp`; require `pip check`, exact development version,
  installed 12-case benchmark success, and installed workbench health body `ok`.
- [ ] Obtain independent review with no unresolved findings.
- [ ] Push a `codex/` branch, open a ready PR, require protected `verify` and CodeQL success, squash
  merge, then require exact merged-main CI and CodeQL success.
- [ ] Fast-forward local main to the exact merge SHA, clean up the branch/worktree, and immediately
  begin the next evidence-backed gap.
