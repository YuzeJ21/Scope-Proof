# Export State Revalidation Implementation Plan

> **For agentic workers:** Use `superpowers:executing-plans` and preserve RED-GREEN evidence for
> every behavior change.

**Goal:** Ensure every JSON, Markdown, CSV, and HTML export validates the complete object at the
export boundary.

**Architecture:** Reconstruct the concrete `ReviewState` or `ReviewBundle` through Pydantic before
any serialization or bundle selection, using one shared reporting helper.

**Tech stack:** Python 3.12, Pydantic v2, pytest, Ruff.

## Constraints

- Reject invalid audit objects; never normalize or select one contradictory identity.
- Preserve deterministic gates, False Ready safety, output fields, and escaping.
- Keep core reporting independent from Streamlit and GitHub UI layers.
- No billing, paid API, LLM API, organization, second account, private repository, fork, untrusted
  execution, synthetic validation, comment, or release.

### Task 1: Add failing export-boundary regressions

**Files:**
- Modify: `tests/reporting/test_exporters.py`

- [ ] Parameterize all four exporters over a validator-bypassed `ReviewState` with contradictory
  active head SHAs; require the active-review identity error.
- [ ] Parameterize all four exporters over a mutated direct `ReviewBundle` with an invalid blank
  base SHA; require the existing SHA validation error.
- [ ] Run focused tests and capture RED: all eight cases currently export successfully.

### Task 2: Revalidate every export input

**Files:**
- Modify: `scopeproof_core/reporting/exporters.py`
- Test: `tests/reporting/test_exporters.py`

- [ ] Add `_validated_exportable(...)` with complete dump-and-revalidate semantics for both accepted
  concrete models.
- [ ] Use it in `export_json(...)` and at the start of `_bundle_and_state(...)`.
- [ ] Run the full reporting suite and Ruff. Require valid output regressions to remain green.

### Task 3: Full verification and protected publication

- [ ] Run Ruff, the complete offline suite, deterministic benchmark, and `git diff --check`.
- [ ] Build and clean-install the wheel under `/tmp`; require dependency health, exact development
  version, installed 12-case benchmark success, and installed workbench health body `ok`.
- [ ] Obtain independent review with no unresolved findings.
- [ ] Push a `codex/` branch, create a ready PR, require protected `verify` and CodeQL success,
  squash merge, and require exact merged-main CI and CodeQL success.
- [ ] Fast-forward local main, clean the worktree/branch, and continue to the next real gap.
