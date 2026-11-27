# CI Outcomes and Evaluation Candidate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Explain changed run assertions inline and retain an exact-source consolidated
evaluation candidate with verified archive and installed-wheel bindings.

**Architecture:** Reuse the existing comparison projection and engineering CI journeys.
Add one distribution-only helper with strict manifest validation, leaving core rules intact.

**Tech Stack:** Existing Python/Pydantic/Streamlit, pytest, Hatchling/uv and GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-11-27-ci-outcomes-evaluation-candidate-design.md`

## Global Constraints

- Candidate version remains `0.2.9.dev0`; public v0.2.8 stays current.
- No evidence/gate/schema/dependency change, frozen-data rewrite, publication or outreach.
- Both archive and verification inputs must be validated before output creation.
- Exact source/tree and exact wheel bytes, rather than filenames alone, bind observations.

## Review Focus

- Outcome-only run changes must be explainable when effective status is unchanged.
- Empty outcomes and absent run records must remain distinguishable.
- A parity-matching wheel must still contain the expected source Python inventory.
- JUnit or probe failure must prevent a ready candidate packet.
- PR merge artifacts must never be labelled reviewed-main candidates.

### Task 1: Show both run outcome assertions

**Files:** `apps/web/ci_comparison.py`, `tests/apps/test_ci_comparison.py`,
`tests/browser/test_workbench_ci_comparison.py`.

**Interfaces:** Existing `CIStatusComparison.run_changes()`; two literal outcome columns
in the run dataframe, deterministically ordered by test identifier.

- [x] Write a failing AppTest assertion for outcome-only changes and absent/empty records.
- [x] Observe failure, add the minimal display projection, and pass comparison regressions.
- [x] Extend the installed journey to check run-context view availability; AppTest pins
  both reported outcome columns. Commit.

### Task 2: Bind evaluation assets to tested bytes

**Files:** Create `scripts/prepare_evaluation_candidate.py` and
`tests/test_evaluation_candidate.py`; modify `.github/workflows/ci.yml`.

**Interfaces:** `prepare_candidate(...) -> CandidateManifest` validates source/archive/test/
probe inputs and writes a new packet; CLI consumes named directories/results/probe inputs.

- [x] Write failing controlled-archive tests for exact hashes and parity, inventory, failed
  verification, source kind and refusal to replace output.
- [x] Implement strict manifest/probe/results schemas and create-only packet preparation.
- [x] Retain source/browser JUnit and use a fixed browser basetemp. Build/rebuild archives
  before long checks to fail early, install that candidate wheel for CLI checks, then probe
  after browser checks; validate bindings and upload the CI artifact.
- [x] Document unpublished candidate consumption and limits; run affected tests and lint.

### Task 3: Review, integrate and retain main candidate

**Files:** Roadmap, changelog, evaluation guide and candidate/audit notes.

- [x] Review the complete branch once; fix important findings with RED/GREEN tests.
- [ ] Sync an exact-tree PR, pass all protected checks and inspect candidate observations.
- [ ] Integrate, verify resulting main and its separately built candidate; record artifact
  identity and next-stage decisions in the PR. Stop before publication or new feature work.
