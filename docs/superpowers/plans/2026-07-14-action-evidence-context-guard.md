# ScopeProof Action-Evidence Context Guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reject content-free required fields in owner-supplied Action validation records while preserving valid offline validation behavior.

**Architecture:** Keep `ActionValidationRecord` as the single Pydantic boundary used by the CLI. Add focused scalar and list-item validators in the schema; do not change the CLI, Action workflow, or external-validation semantics except through the stronger model contract.

**Tech Stack:** Python 3.12, Pydantic 2, pytest, Ruff, argparse CLI

## Global Constraints

- Validation remains offline and must not claim submitted GitHub URLs are genuine.
- Fork testing remains permanently excluded for the single-account public alpha.
- No paid API, billing, organization, second account, private repository, or external comment is introduced.
- Valid field values remain unchanged; this slice does not trim or normalize them.
- No Streamlit, lifecycle, finding, gate, runtime-evidence, final-acceptance, export, or storage-version behavior changes.

---

### Task 1: Required scalar and limitation content validation

**Files:**
- Modify: `tests/schemas/test_action_validation_record.py`
- Modify: `scopeproof_core/schemas/models.py`

**Interfaces:**
- Consumes: `ActionValidationRecord.model_validate(data: object) -> ActionValidationRecord`
- Produces: `ActionValidationRecord.require_non_blank_action_context(value: str) -> str`
- Produces: `ActionValidationRecord.require_non_blank_limitations(value: list[str]) -> list[str]`

- [ ] **Step 1: Add failing parameterized schema tests**

Append tests that reject whitespace-only required scalars and limitation items while preserving
otherwise nonblank human text:

```python
@pytest.mark.parametrize(
    "field_name",
    [
        "requirements_base_sha",
        "non_fork_head_sha",
        "rerun_head_sha",
        "validated_by",
    ],
)
@pytest.mark.parametrize("blank_value", ["   ", "\t", "\n"])
def test_action_validation_record_rejects_blank_required_context(
    field_name: str, blank_value: str
) -> None:
    payload = record_data()
    payload[field_name] = blank_value
    if field_name in {"non_fork_head_sha", "rerun_head_sha"}:
        payload["non_fork_head_sha"] = blank_value
        payload["rerun_head_sha"] = blank_value
        payload["scopeproof_comment_marker"] = f"<!-- scopeproof:{blank_value} -->"

    with pytest.raises(ValueError, match="non-whitespace"):
        ActionValidationRecord.model_validate(payload)


@pytest.mark.parametrize("blank_value", ["   ", "\t", "\n"])
def test_action_validation_record_rejects_blank_limitation(blank_value: str) -> None:
    payload = record_data() | {"limitations": ["Public demo only", blank_value]}

    with pytest.raises(ValueError, match="limitation"):
        ActionValidationRecord.model_validate(payload)


def test_action_validation_record_preserves_valid_human_context() -> None:
    payload = record_data() | {
        "validated_by": "  Demo repository owner  ",
        "limitations": ["  Public demo only  "],
    }

    record = ActionValidationRecord.model_validate(payload)

    assert record.validated_by == "  Demo repository owner  "
    assert record.limitations == ["  Public demo only  "]
```

- [ ] **Step 2: Run the schema tests and verify RED**

Run:

```bash
'../../.venv/bin/python' -m pytest tests/schemas/test_action_validation_record.py -q
```

Expected: the new blank scalar and blank limitation cases fail because the current model accepts
them; the preservation case passes.

- [ ] **Step 3: Add minimal Pydantic validators**

In `ActionValidationRecord`, before `validate_rerun_idempotency`, add:

```python
    @field_validator(
        "requirements_base_sha",
        "non_fork_head_sha",
        "rerun_head_sha",
        "validated_by",
    )
    @classmethod
    def require_non_blank_action_context(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must contain non-whitespace text")
        return value

    @field_validator("limitations")
    @classmethod
    def require_non_blank_limitations(cls, value: list[str]) -> list[str]:
        if any(not limitation.strip() for limitation in value):
            raise ValueError("limitations must contain non-whitespace text")
        return value
```

- [ ] **Step 4: Run the schema tests and verify GREEN**

Run:

```bash
'../../.venv/bin/python' -m pytest tests/schemas/test_action_validation_record.py -q
```

Expected: all Action-validation schema tests pass.

- [ ] **Step 5: Run adjacent schema and CLI regression tests**

Run:

```bash
'../../.venv/bin/python' -m pytest \
  tests/schemas/test_action_validation_record.py \
  tests/cli/test_cli.py -q
```

Expected: valid CLI records still print and all adjacent tests pass.

- [ ] **Step 6: Commit the schema guard**

```bash
git add scopeproof_core/schemas/models.py tests/schemas/test_action_validation_record.py
git commit -m "fix: reject blank action evidence context"
```

---

### Task 2: CLI rejection coverage and complete verification

**Files:**
- Modify: `tests/cli/test_cli.py`

**Interfaces:**
- Consumes: `scopeproof_core.cli.main(argv: list[str] | None = None) -> int`
- Produces: CLI regression proof that invalid Action-evidence JSON exits through argparse and does
  not emit a validated record

- [ ] **Step 1: Add a failing CLI regression test**

Add a helper for valid Action-evidence data if needed, then add:

```python
def test_action_evidence_command_rejects_blank_owner_context(
    tmp_path: Path, capsys
) -> None:
    evidence_path = tmp_path / "blank-action-evidence.json"
    payload = action_evidence_data() | {"validated_by": "   "}
    evidence_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(SystemExit) as error:
        main(["validate-action-evidence", str(evidence_path)])

    assert error.value.code == 2
    captured = capsys.readouterr()
    assert "non-whitespace" in captured.err
    assert '"repository"' not in captured.out
```

If the existing valid CLI test has inline data, extract that unchanged dictionary into
`action_evidence_data()` and use it in both tests.

- [ ] **Step 2: Verify the CLI test already passes through the new schema boundary**

Run:

```bash
'../../.venv/bin/python' -m pytest \
  tests/cli/test_cli.py::test_action_evidence_command_rejects_blank_owner_context -q
```

Expected: PASS because Task 1 already strengthened the authoritative model. This is contract
coverage for the existing CLI path, not a second production-code change.

- [ ] **Step 3: Run focused quality gates**

Run:

```bash
'../../.venv/bin/python' -m ruff check \
  scopeproof_core/schemas/models.py \
  tests/schemas/test_action_validation_record.py \
  tests/cli/test_cli.py
'../../.venv/bin/python' -m pytest \
  tests/schemas/test_action_validation_record.py \
  tests/cli/test_cli.py -q
```

Expected: Ruff is clean and all focused tests pass.

- [ ] **Step 4: Commit CLI contract coverage**

```bash
git add tests/cli/test_cli.py
git commit -m "test: cover blank action evidence CLI input"
```

- [ ] **Step 5: Run complete offline verification**

Run:

```bash
'../../.venv/bin/python' -m ruff check .
'../../.venv/bin/python' -m pytest -q
'../../.venv/bin/python' -m scopeproof_core.cli benchmark
git diff --check main...HEAD
```

Expected: Ruff clean; the full suite passes; all 12 benchmark cases and 13 criteria execute with
zero mismatches, zero must-have False Ready, and zero False Blocker; the diff check is clean.

- [ ] **Step 6: Build and smoke the candidate package**

Build a wheel into a fresh `/tmp` directory, install it in a fresh virtual environment, run
`pip check`, and validate both a valid and blank owner-context Action record through the installed
`scopeproof` CLI.

Expected: the valid record exits `0` and prints validated JSON; the blank record exits `2`, prints
the stable validation error on stderr, and emits no validated JSON on stdout.

- [ ] **Step 7: Review the final branch diff**

Run:

```bash
git status --short --branch
git log --oneline main..HEAD
git diff --stat main...HEAD
git diff --check main...HEAD
```

Expected: only the design, plan, schema, and focused tests differ; the branch is clean.

- [ ] **Step 8: Publish through the protected workflow**

Push `codex/action-evidence-context-guard`, open one focused ready PR, wait for required `verify`
and CodeQL checks, fix only genuine failures, squash-merge when green, synchronize local `main`,
and remove the owned worktree and branch after tree-equivalence verification.

Do not publish a release for this internal validation correction.
