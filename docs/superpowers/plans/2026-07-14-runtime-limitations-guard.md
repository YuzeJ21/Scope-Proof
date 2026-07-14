# Runtime-Evidence Limitations Guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reject whitespace-only runtime-evidence limitation entries at the authoritative Pydantic boundary without normalizing valid evidence text.

**Architecture:** Extend the existing `RuntimeEvidence` model with one focused list validator. Keep Streamlit, lifecycle, exporters, persistence format, evidence levels, final acceptance, and deterministic gates unchanged; all consumers continue to receive already validated model data.

**Tech Stack:** Python 3.12, Pydantic 2, pytest, Ruff, Hatchling wheel build.

## Global Constraints

- Preserve valid limitation strings exactly; do not trim or rewrite them.
- An omitted or empty limitations list remains valid.
- Runtime evidence remains append-only and cannot change static findings, resolutions, final acceptance, or the gate.
- Never execute untrusted PR code or claim controlled fixtures as external runtime evidence.
- No APIs, paid services, billing, telemetry, forks, comments, or release publication.

---

### Task 1: Guard runtime limitation entries

**Files:**
- Modify: `tests/schemas/test_runtime_evidence.py`
- Modify: `scopeproof_core/schemas/models.py`

**Interfaces:**
- Consumes: `RuntimeEvidence.limitations: list[str]`.
- Produces: `RuntimeEvidence.require_non_blank_limitations(cls, value: list[str]) -> list[str]`.

- [ ] **Step 1: Write failing schema regressions**

Add tests that require any whitespace-only list item to fail, valid surrounding whitespace to remain unchanged, and an empty list to remain valid:

```python
def test_runtime_evidence_rejects_whitespace_only_limitation() -> None:
    payload = runtime_evidence_payload()
    payload["limitations"] = ["Manual observation only", " \t\n "]

    with pytest.raises(ValueError, match="limitations must contain non-whitespace text"):
        RuntimeEvidence(**payload)


def test_runtime_evidence_preserves_nonblank_limitation_exactly() -> None:
    payload = runtime_evidence_payload()
    payload["limitations"] = ["  retained limitation text  "]

    evidence = RuntimeEvidence(**payload)

    assert evidence.limitations == ["  retained limitation text  "]


def test_runtime_evidence_accepts_empty_limitations() -> None:
    payload = runtime_evidence_payload()
    payload["limitations"] = []

    evidence = RuntimeEvidence(**payload)

    assert evidence.limitations == []
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```bash
PYTHONPATH="$PWD" /Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m pytest \
  tests/schemas/test_runtime_evidence.py -k limitations -q
```

Expected: the whitespace-only regression fails because current Pydantic construction accepts the list; the preservation and empty-list cases pass.

- [ ] **Step 3: Add the minimal Pydantic validator**

Add this validator to `RuntimeEvidence` after `require_non_blank_human_context`:

```python
    @field_validator("limitations")
    @classmethod
    def require_non_blank_limitations(cls, value: list[str]) -> list[str]:
        if any(not limitation.strip() for limitation in value):
            raise ValueError("limitations must contain non-whitespace text")
        return value
```

- [ ] **Step 4: Run focused GREEN and adjacent exporter coverage**

Run:

```bash
PYTHONPATH="$PWD" /Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m pytest -q \
  tests/schemas/test_runtime_evidence.py \
  tests/reviews/test_lifecycle.py::test_runtime_evidence_is_append_only_and_does_not_change_gate \
  tests/reporting/test_exporters.py
```

Expected: all selected tests pass with no warnings or errors.

- [ ] **Step 5: Commit the implementation**

```bash
git add scopeproof_core/schemas/models.py tests/schemas/test_runtime_evidence.py
git diff --cached --check
git commit -m "Reject blank runtime limitations"
```

### Task 2: Verify and publish the bounded fix

**Files:**
- Verify: repository source, tests, benchmark fixtures, and archived wheel.

**Interfaces:**
- Consumes: committed `RuntimeEvidence` validator.
- Produces: protected-main merge evidence for the exact commit.

- [ ] **Step 1: Run all local gates**

Run:

```bash
PYTHONPATH="$PWD" /Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m ruff check .
PYTHONPATH="$PWD" /Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m pytest -q
PYTHONPATH="$PWD" /Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m scopeproof_core.evals.runner
git diff --check main...HEAD
```

Require Ruff success, all tests passing except the intentional skip, 12 benchmark cases, 0 mismatches, 0 must-have false-ready, 0 false blocker, and a clean diff check.

- [ ] **Step 2: Verify a clean archived wheel**

Archive `HEAD`, build a wheel from only that archive, install it into a fresh target, and run a direct installed-package probe. Require whitespace-only limitation rejection, exact preservation of a valid surrounding-whitespace value, and a successful installed benchmark with 0 mismatches, 0 must-have false-ready, and 0 false blocker.

- [ ] **Step 3: Publish through protected GitHub workflow**

Push `codex/runtime-limitations-guard`, open one ready PR, and merge only after CI `verify`, ScopeProof evidence review, and CodeQL succeed. Then require CI and CodeQL success for the exact squash-merge SHA, fast-forward local `main`, and remove the temporary worktree and branch. Do not publish a release for this schema-only maintenance slice.
