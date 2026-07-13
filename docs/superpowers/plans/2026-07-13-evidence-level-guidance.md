# Evidence-Level Guidance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Define ScopeProof's evidence levels at the criteria and evidence-matrix decision surfaces
without changing evidence or gate behavior.

**Architecture:** Add two UI-only Streamlit captions that restate the existing EvidenceLevel schema
contract at the point of use. Move the single source version to `0.1.16.dev0` because v0.1.15 is now
published; leave README's verified-wheel installation guidance at v0.1.15.

**Tech Stack:** Python 3.11+, Streamlit AppTest, Pydantic 2, pytest, Ruff, Hatchling.

## Global Constraints

- Criteria guidance defines E1, E2, and E3 and says static PR analysis can produce only E1 or E2.
- Matrix guidance defines E0 through E4 and says levels describe evidence type, not correctness.
- EvidenceLevel enum values, ranks, retrieval, verification, gates, persistence, exports, runtime
  evidence, resolution, and final acceptance remain unchanged.
- `scopeproof_core/version.py` is the only checked-in version value and becomes `0.1.16.dev0`.
- README continues to install the verified public v0.1.15 wheel.
- No paid API, billing, private repository, fork test, external service, or untrusted-code execution.

---

### Task 1: Add point-of-use evidence-level guidance

**Files:**
- Modify: `tests/apps/test_streamlit_app.py`
- Modify: `tests/test_repository_contracts.py`
- Modify: `apps/web/app.py`
- Modify: `scopeproof_core/version.py`

**Interfaces:**
- Produces criteria caption:
  `Evidence levels set the minimum proof needed for each criterion: E1 = implementation or contract candidate; E2 = test candidate; E3 = manually recorded runtime verification. Static PR analysis can produce only E1 or E2.`
- Produces matrix caption:
  `Evidence levels: E0 = no candidate found; E1 = implementation or contract candidate; E2 = test candidate; E3 = manually recorded runtime verification; E4 = explicit human acceptance. Levels describe evidence type, not correctness.`
- Produces package and new-review development version `0.1.16.dev0`

- [ ] **Step 1: Write failing UI and version contract tests**

Add to `tests/apps/test_streamlit_app.py`:

```python
def test_criteria_confirmation_explains_required_evidence_levels() -> None:
    app = load_demo(new_app())
    caption_text = "\n".join(item.value for item in app.caption)

    assert (
        "Evidence levels set the minimum proof needed for each criterion: "
        "E1 = implementation or contract candidate; E2 = test candidate; "
        "E3 = manually recorded runtime verification. Static PR analysis can produce "
        "only E1 or E2."
    ) in caption_text


def test_evidence_matrix_explains_observed_evidence_levels() -> None:
    app = analyzed_demo(new_app())
    caption_text = "\n".join(item.value for item in app.caption)

    assert (
        "Evidence levels: E0 = no candidate found; E1 = implementation or contract candidate; "
        "E2 = test candidate; E3 = manually recorded runtime verification; "
        "E4 = explicit human acceptance. Levels describe evidence type, not correctness."
    ) in caption_text
```

In `tests/test_repository_contracts.py`, change the version-source assertion to:

```python
    assert '__version__ = "0.1.16.dev0"' in version_source
```

- [ ] **Step 2: Run focused tests and verify RED**

Run:

```bash
../../.venv/bin/python -m pytest \
  tests/apps/test_streamlit_app.py::test_criteria_confirmation_explains_required_evidence_levels \
  tests/apps/test_streamlit_app.py::test_evidence_matrix_explains_observed_evidence_levels \
  tests/test_repository_contracts.py::test_hatch_and_reviews_share_one_version_source -q
```

Expected: three failures because both captions are absent and the source still reports `0.1.15`.

- [ ] **Step 3: Add the criteria caption**

Inside the non-empty criteria branch immediately after `else:`, add:

```python
    st.caption(
        "Evidence levels set the minimum proof needed for each criterion: "
        "E1 = implementation or contract candidate; E2 = test candidate; "
        "E3 = manually recorded runtime verification. Static PR analysis can produce "
        "only E1 or E2."
    )
```

- [ ] **Step 4: Add the matrix caption**

Inside the analyzed matrix branch immediately after `else:`, add:

```python
    st.caption(
        "Evidence levels: E0 = no candidate found; "
        "E1 = implementation or contract candidate; E2 = test candidate; "
        "E3 = manually recorded runtime verification; E4 = explicit human acceptance. "
        "Levels describe evidence type, not correctness."
    )
```

- [ ] **Step 5: Mark the post-release development line**

Set `scopeproof_core/version.py` to:

```python
"""Single checked-in source for ScopeProof package and review provenance."""

__version__ = "0.1.16.dev0"
```

Do not change README's v0.1.15 installation URLs.

- [ ] **Step 6: Run focused tests and verify GREEN**

Run the command from Step 2.

Expected: `3 passed`.

- [ ] **Step 7: Run adjacent UI regressions**

Run:

```bash
../../.venv/bin/python -m pytest tests/apps/test_streamlit_app.py \
  tests/test_repository_contracts.py -q
```

Expected: all selected tests pass with no warning or error output.

- [ ] **Step 8: Commit the bounded implementation**

```bash
git add apps/web/app.py scopeproof_core/version.py \
  tests/apps/test_streamlit_app.py tests/test_repository_contracts.py
git commit -m "clarify evidence levels in review flow"
```

### Task 2: Verify packaging and the live flow

**Files:**
- Verify: all branch changes
- Build transiently under: `/tmp/scopeproof-evidence-level-guidance-*`
- Save screenshots under the existing v0.1.15 first-use audit folder

**Interfaces:**
- Consumes: Task 1 implementation
- Produces: full source, clean-wheel, HTTP, and before/after visual evidence

- [ ] **Step 1: Run all source gates**

Run:

```bash
../../.venv/bin/python -m ruff check .
../../.venv/bin/python -m pytest -q
../../.venv/bin/python -m scopeproof_core.evals.runner
git diff origin/main...HEAD --check
```

Expected: Ruff passes; all offline tests pass with only the intentional live-network skip; all 12
benchmark cases execute with zero mismatches, zero must-have False Ready, and zero false blocker;
the diff check is clean.

- [ ] **Step 2: Build and verify a clean development wheel**

Build exactly one `scopeproof-0.1.16.dev0-py3-none-any.whl`, install it into a fresh environment,
and from `/tmp` require distribution version, module version, both console versions, and a new
Review's tool version to equal `0.1.16.dev0`. Run the installed benchmark.

- [ ] **Step 3: Run the packaged workbench**

Start the installed workbench on a fresh explicit loopback port, require exact `ok` from
`/_stcore/health`, and keep it running for browser verification.

- [ ] **Step 4: Capture and inspect the updated criteria state**

Load the deliberately constructed demo, scroll to `2 · Confirm Criteria`, require the E1/E2/E3
caption in the latest DOM, and save `07-criteria-guidance.png`.

- [ ] **Step 5: Capture and inspect the updated matrix state**

Confirm criteria, run deterministic analysis, scroll to `3 · Evidence Matrix`, require the E0-E4
caption in the latest DOM, and save `08-matrix-guidance.png`.

- [ ] **Step 6: Compare before and after together**

Inspect `02-criteria.png` beside `07-criteria-guidance.png`, and `04-matrix.png` beside
`08-matrix-guidance.png`, in the same comparison input. Confirm the captions are readable, controls
remain aligned, and no new clipping or hierarchy problem appears.

- [ ] **Step 7: Stop the server and review scope**

Require no traceback, clean branch status, and a diff limited to design, plan, two captions, version
marker, and regression tests. Confirm no schema, gate, persistence, export, dependency, or workflow
change.

### Task 3: Integrate through protected main

**Files:**
- Publish branch: `codex/evidence-level-guidance`

**Interfaces:**
- Consumes: fully verified branch
- Produces: protected-main evidence-level guidance on the v0.1.16 development line

- [ ] **Step 1: Push and open one protected pull request**

Summarize the audit finding, exact UI copy, version marker, and fresh verification. State that the
browser/AppTest evidence is controlled product evidence, not external validation. Do not add an
issue comment, reviewer request, or release.

- [ ] **Step 2: Wait for all checks and merge only when green**

Require both verify runs, CodeQL language jobs and aggregate, and the informational ScopeProof job
to pass. Merge only with clean protected status.

- [ ] **Step 3: Verify merged main and clean up**

Require merged-main CI and CodeQL success, fast-forward local main, confirm clean
`HEAD == origin/main`, remove the owned worktree and merged branch, and verify v0.1.15 remains the
latest release with no new issue comment.
