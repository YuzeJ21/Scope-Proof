# Finding Context Guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reject whitespace-only finding explanations, recovery actions, missing-evidence entries, and contradiction entries before a verdict can be persisted or exported.

**Architecture:** Add focused Pydantic validators to the existing UI-independent `Finding` model. Keep verification, gates, exporters, Streamlit, and version behavior unchanged; every consumer receives the same validated finding context.

**Tech Stack:** Python 3.12, Pydantic 2, pytest, Ruff, GitHub Actions, GitHub CLI.

## Global Constraints

- Preserve valid finding text and list members exactly; do not strip, infer, reorder, or deduplicate.
- Empty `missing_evidence` and `contradictions` lists remain valid.
- Keep finding statuses, evidence IDs, levels, confidence, gate precedence, and version `0.1.18.dev0` unchanged.
- Do not create issue comments, reviewer requests, releases, fork tests, or notification-only work.
- Controlled validation is not external runtime evidence, customer validation, or adoption.

---

### Task 1: Enforce explicit finding context

**Files:**
- Modify: `tests/schemas/test_models.py`
- Modify: `scopeproof_core/schemas/models.py:390-399`

**Interfaces:**
- Consumes: `Finding.model_validate(value) -> Finding`.
- Produces: nonblank `reason` and `recommended_action`; supplied `missing_evidence` and `contradictions` members that contain non-whitespace text; unchanged valid values.

- [ ] **Step 1: Add a valid finding payload and failing required-text tests**

Add `Finding` and `FindingStatus` to the schema imports in `tests/schemas/test_models.py`, then add:

```python
def finding_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "criterion_id": "AC-01",
        "status": FindingStatus.MISSING,
        "reason": "No candidate evidence was found.",
        "missing_evidence": ["Required evidence level E1"],
        "contradictions": [],
        "recommended_action": "Add or identify candidate evidence.",
    }
    payload.update(overrides)
    return payload


@pytest.mark.parametrize("field", ["reason", "recommended_action"])
@pytest.mark.parametrize("blank", ["", "   ", "\t\n"])
def test_finding_context_rejects_blank_required_text(field: str, blank: str) -> None:
    with pytest.raises(ValidationError, match="must contain non-whitespace text"):
        Finding.model_validate(finding_payload(**{field: blank}))
```

- [ ] **Step 2: Add failing list-member tests and valid controls**

Add:

```python
@pytest.mark.parametrize("field", ["missing_evidence", "contradictions"])
@pytest.mark.parametrize("blank", ["", "   ", "\t\n"])
def test_finding_context_rejects_blank_list_member(field: str, blank: str) -> None:
    with pytest.raises(
        ValidationError, match="finding context must contain non-whitespace text"
    ):
        Finding.model_validate(finding_payload(**{field: [blank]}))


def test_finding_context_preserves_valid_text_exactly() -> None:
    finding = Finding.model_validate(
        finding_payload(
            reason="  No candidate evidence was found.  ",
            recommended_action="  Add candidate evidence.  ",
            missing_evidence=["  Required evidence level E1  "],
            contradictions=["  Conflicting implementation  "],
        )
    )

    assert finding.reason == "  No candidate evidence was found.  "
    assert finding.recommended_action == "  Add candidate evidence.  "
    assert finding.missing_evidence == ["  Required evidence level E1  "]
    assert finding.contradictions == ["  Conflicting implementation  "]


def test_finding_context_allows_empty_optional_lists() -> None:
    finding = Finding.model_validate(
        finding_payload(missing_evidence=[], contradictions=[])
    )

    assert finding.missing_evidence == []
    assert finding.contradictions == []
```

- [ ] **Step 3: Run focused RED**

```bash
PYTHONPATH="$PWD" /Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m pytest -q \
  tests/schemas/test_models.py -k finding_context
```

Expected: 12 failures for blank required strings and list members; two valid controls pass.

- [ ] **Step 4: Add the minimal Pydantic validators**

Add to `Finding` in `scopeproof_core/schemas/models.py`:

```python
    @field_validator("reason", "recommended_action", mode="before")
    @classmethod
    def require_non_blank_explanation(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            raise ValueError("must contain non-whitespace text")
        return value

    @field_validator("missing_evidence", "contradictions")
    @classmethod
    def require_non_blank_context(cls, value: list[str]) -> list[str]:
        if any(not item.strip() for item in value):
            raise ValueError("finding context must contain non-whitespace text")
        return value
```

- [ ] **Step 5: Run focused GREEN and related contracts**

Repeat Step 3 and require 14 passes. Then run:

```bash
PYTHONPATH="$PWD" /Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m pytest -q \
  tests/schemas tests/verification tests/gates tests/reporting tests/reviews tests/storage
```

Require all selected tests to pass.

- [ ] **Step 6: Commit the bounded implementation**

```bash
git add scopeproof_core/schemas/models.py tests/schemas/test_models.py
git diff --cached --check
git commit -m "Reject blank finding context"
```

### Task 2: Verify, integrate, and reconcile

**Files:**
- Verify: branch source and an archived build under `/tmp/scopeproof-finding-context-*`.
- Publish: `codex/finding-context-guard` through one protected pull request.

**Interfaces:**
- Consumes: the validators and tests from Task 1.
- Produces: one exact protected merge SHA with successful CI and CodeQL.

- [ ] **Step 1: Run full source gates**

Run Ruff, complete pytest, `python -m scopeproof_core.evals.runner`, and
`git diff --check main...HEAD`. Require 422 passed and 1 skipped; benchmark 12 cases, 13 criteria,
0 mismatches, 0 must-have false-ready, and 0 false blockers.

- [ ] **Step 2: Verify an archived installed wheel**

Build exactly `scopeproof-0.1.18.dev0-py3-none-any.whl` from `git archive HEAD`, install it with
declared dependencies in a fresh virtual environment, and require `pip check`. Outside the source
checkout, require distribution, module, CLI, web launcher, and new-review provenance identity
`0.1.18.dev0`; reject all 12 blank cases; preserve valid strings and list members; and accept empty
optional lists.

- [ ] **Step 3: Verify installed benchmark and workbench health**

Require installed benchmark 12/13/0/0/0. Start installed `scopeproof-web` at
`127.0.0.1:8518` with temporary `HOME`, require exact response `ok`, terminate cleanly, and reject
`Traceback` in the log.

- [ ] **Step 4: Publish one ready PR**

Push `codex/finding-context-guard`. Open one ready PR describing the reproduced blank exported
finding, RED/GREEN evidence, source and installed verification, unchanged gate/export behavior, and
the permanent no-cost/no-fork boundaries. Do not comment on issue #3, request a reviewer, or publish
a release.

- [ ] **Step 5: Merge only after protected checks**

Require both `verify` checks, ScopeProof evidence review, CodeQL language jobs, and aggregate
CodeQL success. Squash merge, record the exact merge SHA, fast-forward local `main`, and require CI
and CodeQL success for that SHA.

- [ ] **Step 6: Clean and continue**

Remove the clean worktree and feature branch, prune the remote, require no open PRs and a clean
synchronized `main`, retain v0.1.17 as latest release, and rotate immediately to the next
evidence-backed loop.
