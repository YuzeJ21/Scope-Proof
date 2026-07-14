# Requirements Confirmer Guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reject whitespace-only owner identity in hash-bound GitHub Action requirements confirmation records before the workflow can mark requirements confirmed.

**Architecture:** Keep digest comparison, CLI recovery, and workflow behavior unchanged. Enforce explicit non-whitespace identity once in the `RequirementsConfirmation` Pydantic model so direct callers, the CLI, and the Action share the same rule.

**Tech Stack:** Python 3.12, Pydantic 2, pytest, Ruff, GitHub Actions, GitHub CLI.

## Global Constraints

- Preserve valid `confirmed_by` values exactly; do not strip or normalize them.
- Keep requirements SHA-256 and timestamp contracts unchanged.
- Do not change workflow permissions, comment behavior, gate semantics, or version `0.1.18.dev0`.
- Do not create issue comments, reviewer requests, releases, fork tests, or notification-only work.
- Controlled validation is not authenticated identity, external runtime evidence, customer validation, or adoption.

---

### Task 1: Enforce explicit confirmer identity

**Files:**
- Modify: `tests/criteria/test_confirmation.py`
- Modify: `tests/cli/test_cli.py`
- Modify: `scopeproof_core/criteria/confirmation.py:9-19`

**Interfaces:**
- Consumes: `validate_requirements_confirmation(requirements_path: Path, confirmation_path: Path) -> RequirementsConfirmation`.
- Produces: `RequirementsConfirmation.confirmed_by` that rejects whitespace-only strings with the stable message `confirmed_by must contain non-whitespace text` and preserves valid strings exactly.

- [ ] **Step 1: Add file-backed failing schema tests**

Add to `tests/criteria/test_confirmation.py`:

```python
@pytest.mark.parametrize("confirmed_by", ["", "   ", "\t\n"])
def test_confirmation_record_rejects_blank_confirmer(
    tmp_path: Path, confirmed_by: str
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("Document the validation demo.\n", encoding="utf-8")
    payload = confirmation_payload(requirements.read_text())
    payload["confirmed_by"] = confirmed_by
    record = tmp_path / "confirmation.json"
    record.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="confirmed_by must contain non-whitespace text"):
        validate_requirements_confirmation(requirements, record)


def test_confirmation_record_preserves_valid_confirmer_text(tmp_path: Path) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("Document the validation demo.\n", encoding="utf-8")
    payload = confirmation_payload(requirements.read_text())
    payload["confirmed_by"] = "  Demo owner  "
    record = tmp_path / "confirmation.json"
    record.write_text(json.dumps(payload), encoding="utf-8")

    confirmation = validate_requirements_confirmation(requirements, record)

    assert confirmation.confirmed_by == "  Demo owner  "
```

- [ ] **Step 2: Add the CLI recovery regression**

Add after `test_requirements_confirmation_command_validates_bound_record` in
`tests/cli/test_cli.py`:

```python
def test_requirements_confirmation_command_rejects_blank_confirmer(
    tmp_path: Path, capsys
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("Document the demo.\n", encoding="utf-8")
    confirmation = tmp_path / "confirmation.json"
    confirmation.write_text(
        json.dumps(
            {
                "requirements_sha256": hashlib.sha256(requirements.read_bytes()).hexdigest(),
                "confirmed_by": "   ",
                "confirmed_at": "2026-07-12T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(SystemExit) as error:
        main(
            [
                "validate-requirements-confirmation",
                "--requirements",
                str(requirements),
                "--confirmation",
                str(confirmation),
            ]
        )

    assert error.value.code == 2
    captured = capsys.readouterr()
    assert "confirmed_by must contain non-whitespace text" in captured.err
    assert captured.out == ""
```

- [ ] **Step 3: Run focused RED**

Run:

```bash
PYTHONPATH="$PWD" /Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m pytest -q \
  tests/criteria/test_confirmation.py tests/cli/test_cli.py \
  -k 'confirmation and (blank_confirmer or preserves_valid_confirmer)'
```

Expected: four failures for the three blank file-backed cases and the CLI case; the preservation
control passes.

- [ ] **Step 4: Add the minimal Pydantic validator**

Change the Pydantic import and model in `scopeproof_core/criteria/confirmation.py` to:

```python
from pydantic import BaseModel, ConfigDict, Field, field_validator


class RequirementsConfirmation(BaseModel):
    """A human confirmation bound to the exact bytes of a requirements file."""

    model_config = ConfigDict(extra="forbid")

    requirements_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    confirmed_by: str = Field(min_length=1)
    confirmed_at: datetime

    @field_validator("confirmed_by", mode="before")
    @classmethod
    def require_non_blank_confirmer(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            raise ValueError("confirmed_by must contain non-whitespace text")
        return value
```

- [ ] **Step 5: Run focused GREEN and related contracts**

Repeat Step 3 and require five passes. Then run:

```bash
PYTHONPATH="$PWD" /Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m pytest -q \
  tests/criteria/test_confirmation.py tests/cli/test_cli.py \
  tests/github_action/test_workflow_files.py
```

Expected: all selected tests pass.

- [ ] **Step 6: Commit the bounded implementation**

```bash
git add scopeproof_core/criteria/confirmation.py \
  tests/criteria/test_confirmation.py tests/cli/test_cli.py
git diff --cached --check
git commit -m "Reject blank requirements confirmer"
```

### Task 2: Verify, integrate, and reconcile

**Files:**
- Verify: branch source and a `git archive HEAD` build under `/tmp/scopeproof-requirements-confirmer-*`.
- Publish: `codex/requirements-confirmer-guard` through one protected pull request.

**Interfaces:**
- Consumes: the validator and tests from Task 1.
- Produces: one exact protected merge SHA with successful CI and CodeQL.

- [ ] **Step 1: Run full source gates**

```bash
PYTHONPATH="$PWD" /Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m ruff check .
PYTHONPATH="$PWD" /Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m pytest -q
PYTHONPATH="$PWD" /Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m scopeproof_core.evals.runner
git diff --check main...HEAD
```

Require Ruff success, 408 passed and 1 skipped, benchmark 12 cases/13 criteria/0 mismatches/0
must-have false-ready/0 false blockers, and a clean diff check.

- [ ] **Step 2: Build and install an archived wheel**

Create a fresh `/tmp/scopeproof-requirements-confirmer-*` directory, extract `git archive HEAD`,
build exactly `scopeproof-0.1.18.dev0-py3-none-any.whl`, create a fresh virtual environment, install
the wheel with declared dependencies, and require `pip check`.

- [ ] **Step 3: Run installed identity and confirmation probes**

Outside the source checkout, require distribution metadata, module, CLI, web launcher, and a new
`Review.tool_version` to equal `0.1.18.dev0`. Use temporary requirements and confirmation files to
prove empty, spaces-only, and tab/newline-only `confirmed_by` values fail; prove
`"  Demo owner  "` is preserved exactly.

- [ ] **Step 4: Run installed benchmark and loopback health**

Require the installed benchmark to report 12 cases, 13 criteria, no mismatches, no must-have
false-ready, and no false blockers. Start the installed workbench at `127.0.0.1:8518` with a
temporary `HOME`, require exact health response `ok`, terminate cleanly, and reject `Traceback` in
the log.

- [ ] **Step 5: Push and open one ready PR**

Push `codex/requirements-confirmer-guard`. The PR must include the reproduced workflow-boundary
evidence, RED/GREEN counts, full and installed verification, unchanged digest/permission/gate
semantics, and the permanent no-cost/no-fork boundaries. Do not comment on issue #3, request a
reviewer, or publish a release.

- [ ] **Step 6: Require protected checks and exact merged-main evidence**

Wait for both `verify` checks, ScopeProof evidence review, CodeQL language jobs, and aggregate
CodeQL success. Squash merge only when all pass. Record the merge SHA, fast-forward local `main`,
and require CI and CodeQL success for that exact SHA.

- [ ] **Step 7: Clean and continue**

Remove the clean worktree and local feature branch, prune the deleted remote branch, require no
open PRs and a clean synchronized `main`, keep v0.1.17 as the latest release, and rotate the active
goal into the next evidence-backed loop.
