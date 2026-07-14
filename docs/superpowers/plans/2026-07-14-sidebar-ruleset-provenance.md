# Sidebar Ruleset Provenance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this
> plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the persistent Streamlit sidebar show the validated active review's historical
ruleset version, or the current checked-in ruleset before analysis exists.

**Architecture:** Keep the change inside the Streamlit presentation layer. Import the existing
`RULESET_VERSION`, derive one context-aware caption value from the existing active `bundle`, and
leave all review, lifecycle, storage, gate, and export contracts unchanged.

**Tech Stack:** Python 3.12, Pydantic v2, Streamlit AppTest, pytest, Ruff.

## Global Constraints

- An active analysis displays `bundle.review.ruleset_version`.
- A blank or pre-analysis workbench displays `RULESET_VERSION`.
- The caption suffix remains exactly `local-first · public repositories only`.
- No schema, gate, lifecycle, storage, export, evidence-rule, dependency, workflow, or package
  version change.
- No paid or LLM API, billing, fork, organization, second account, private repository, synthetic
  validation, notification, or untrusted-code execution.

---

### Task 1: Context-aware sidebar provenance

**Files:**
- Modify: `tests/apps/test_streamlit_app.py`
- Modify: `apps/web/app.py`

**Interfaces:**
- Consumes: `RULESET_VERSION` and the existing `bundle: ReviewBundle | None` local.
- Produces: a sidebar caption whose version is the active review version when analysis exists,
  otherwise the current ruleset constant.

- [ ] **Step 1: Write the failing historical-review regression**

Import `RULESET_VERSION`, `JsonReviewStore`, and `default_local_review_directory` in the AppTest
module. Add a test that creates and saves an analyzed demo under a temporary `HOME`, copies both
the lifecycle review and active bundle review with `ruleset_version="0.9.0"`, reopens the validated
record in a fresh AppTest session, and requires this exact sidebar caption:

```python
"Ruleset 0.9.0 · local-first · public repositories only"
```

The same test first requires a blank workbench to show:

```python
f"Ruleset {RULESET_VERSION} · local-first · public repositories only"
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
PYTHONPATH=. ../../.venv/bin/python -m pytest \
  tests/apps/test_streamlit_app.py::test_sidebar_uses_active_review_ruleset_provenance -q
```

Expected: one assertion failure because the reopened historical review still renders the literal
`Ruleset 1.0.0`.

- [ ] **Step 3: Implement the minimal caption source**

Add `RULESET_VERSION` to the existing import from `scopeproof_core.schemas.models`. After the
existing `has_analysis = bundle is not None` assignment, derive:

```python
sidebar_ruleset_version = (
    bundle.review.ruleset_version if bundle is not None else RULESET_VERSION
)
```

Replace the literal sidebar caption with:

```python
st.caption(
    f"Ruleset {sidebar_ruleset_version} · local-first · public repositories only"
)
```

- [ ] **Step 4: Verify GREEN and adjacent sidebar contracts**

Run the focused regression, all sidebar-selected AppTests, Ruff on the changed files, and
`git diff --check`. Require the historical caption, current caption, navigation copy, and locked
status contracts to pass unchanged.

- [ ] **Step 5: Commit the bounded change**

Commit the app, regression test, design, and plan as `Preserve sidebar ruleset provenance`.

### Task 2: Complete candidate verification and protected integration

**Files:**
- Verify: complete repository and installed workbench.

**Interfaces:**
- Consumes: the committed presentation-only change.
- Produces: an exact protected-main commit with local, packaged, runtime, CI, and CodeQL evidence.

- [ ] **Step 1: Run complete local gates**

Run Ruff, the full offline pytest suite, the deterministic benchmark, `pip check`, and
`git diff --check origin/main...HEAD`. Require the single intentional live skip, 12 executed
benchmark cases, 13 executed criteria, zero mismatches, zero must-have False Ready, and zero false
blockers.

- [ ] **Step 2: Verify packaged runtime behavior**

Build from `git archive HEAD`, install the wheel in a fresh `/tmp` environment, require
`pip check`, start `scopeproof-web` on loopback with a temporary `HOME`, and require
`/_stcore/health` to return exact `ok` without traceback.

- [ ] **Step 3: Verify the browser presentation**

Run the constructed demo through analysis in the in-app browser and require the current active
review caption to agree with its validated ruleset. Save and inspect one accepted screenshot.

- [ ] **Step 4: Integrate through protected main**

Push `codex/sidebar-ruleset-provenance`, open one ready PR without labels, reviewers, issue
comments, or manually sent email, require `verify` and CodeQL to pass at the exact head SHA,
squash-merge only while the head remains unchanged, fast-forward local main, and rerun exact-main
verification. Do not publish a release because the change does not alter installation,
distribution, public integration, or release-facing behavior.
