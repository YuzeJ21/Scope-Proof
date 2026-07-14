# Runtime-Evidence Schema Guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reject whitespace-only required manual runtime-evidence fields in the Pydantic schema without changing valid evidence text, Streamlit behavior, final acceptance, or gate semantics.

**Architecture:** Add one focused `field_validator` to the existing `RuntimeEvidence` model and lock its behavior with parameterized schema tests. Keep Streamlit's prerequisite check as the first layer and Pydantic as defense in depth for persisted, imported, and future non-UI records.

**Tech Stack:** Python 3.12, Pydantic 2, pytest, Ruff, Hatchling, Streamlit AppTest, in-app Browser.

## Global Constraints

- Keep development version exactly `0.1.17.dev0`; README continues to install the verified `v0.1.16` release.
- Preserve valid nonblank runtime-evidence strings exactly; do not trim or normalize them.
- Keep `RuntimeEvidence` restricted to E3 and E4.
- Do not change Streamlit labels, readiness logic, recovery copy, reset behavior, findings, resolutions, final acceptance, gates, exports, persistence format, or record version.
- Never execute pull-request code or represent the deliberately constructed demo as external runtime evidence.
- Do not add dependencies, APIs, billing, telemetry, forks, external-validation claims, comments, reviewer requests, or release churn.

---

### Task 1: Pydantic nonblank runtime-evidence contract

**Files:**
- Modify: `tests/schemas/test_runtime_evidence.py`
- Modify: `scopeproof_core/schemas/models.py:297-318`

**Interfaces:**
- Consumes: `RuntimeEvidence(BaseModel)` required fields `artifact_reference`, `scenario`, `environment`, `result`, and `reviewer`.
- Produces: `RuntimeEvidence.require_non_blank_human_context(value: str) -> str`, which rejects whitespace-only values and returns valid values unchanged.

- [ ] **Step 1: Add failing parameterized schema tests**

Append the following helpers and tests to `tests/schemas/test_runtime_evidence.py`:

```python
REQUIRED_RUNTIME_TEXT_FIELDS = [
    "artifact_reference",
    "scenario",
    "environment",
    "result",
    "reviewer",
]


def runtime_evidence_payload() -> dict:
    return {
        "criterion_id": "AC-01",
        "artifact_reference": "https://example.test/run/42",
        "scenario": "Export CSV with an active filter",
        "environment": "staging",
        "result": "passed",
        "reviewer": "A reviewer",
        "evidence_level": EvidenceLevel.E3,
    }


@pytest.mark.parametrize("field_name", REQUIRED_RUNTIME_TEXT_FIELDS)
def test_runtime_evidence_rejects_whitespace_only_required_text(field_name: str) -> None:
    payload = runtime_evidence_payload()
    payload[field_name] = " \t\n "

    with pytest.raises(ValueError, match="must contain non-whitespace text"):
        RuntimeEvidence(**payload)


@pytest.mark.parametrize("field_name", REQUIRED_RUNTIME_TEXT_FIELDS)
def test_runtime_evidence_preserves_nonblank_text_exactly(field_name: str) -> None:
    payload = runtime_evidence_payload()
    payload[field_name] = "  retained evidence text  "

    evidence = RuntimeEvidence(**payload)

    assert getattr(evidence, field_name) == "  retained evidence text  "
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```bash
'../../.venv/bin/python' -m pytest tests/schemas/test_runtime_evidence.py -q
```

Expected: the five whitespace-rejection cases fail because the current `min_length=1` fields accept whitespace; the two existing tests and five preservation cases pass.

- [ ] **Step 3: Add the minimal model validator**

In `RuntimeEvidence`, immediately before `validate_manual_level`, add:

```python
    @field_validator(
        "artifact_reference",
        "scenario",
        "environment",
        "result",
        "reviewer",
    )
    @classmethod
    def require_non_blank_human_context(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must contain non-whitespace text")
        return value
```

The module already imports `field_validator`; do not add another import.

- [ ] **Step 4: Run the focused schema and lifecycle tests and verify GREEN**

Run:

```bash
'../../.venv/bin/python' -m pytest \
  tests/schemas/test_runtime_evidence.py \
  tests/reviews/test_lifecycle.py -q
```

Expected: all focused tests pass; runtime evidence remains append-only and the gate remains unchanged.

- [ ] **Step 5: Run the Streamlit runtime-evidence boundary tests**

Run:

```bash
'../../.venv/bin/python' -m pytest tests/apps/test_streamlit_app.py \
  -k 'runtime_evidence or final_acceptance' -q
```

Expected: prerequisite disabling, stable copy, reset-after-save, final-acceptance independence, and blocker precedence all pass unchanged.

- [ ] **Step 6: Commit the schema contract**

```bash
git add scopeproof_core/schemas/models.py tests/schemas/test_runtime_evidence.py
git diff --cached --check
git commit -m "fix: reject blank runtime evidence context"
```

### Task 2: Source and installed-package verification

**Files:**
- Verify: repository source and a fresh wheel under `/tmp/scopeproof-runtime-schema-*`.

**Interfaces:**
- Consumes: checked-in `0.1.17.dev0` version source, Pydantic schema, deterministic benchmark, `scopeproof`, and `scopeproof-web` entry points.
- Produces: source-test evidence, a clean-installed wheel, an installed schema probe, and exact local web health.

- [ ] **Step 1: Run source gates**

```bash
'../../.venv/bin/python' -m ruff check .
'../../.venv/bin/python' -m pytest -q
'../../.venv/bin/python' -m scopeproof_core.evals.runner
git diff main...HEAD --check
```

Expected: Ruff passes; 255 tests pass with 1 intentional live skip; the benchmark executes 12 cases and 13 criteria with zero mismatches, zero must-have False Ready, and zero false blockers; diff check is clean.

- [ ] **Step 2: Build and clean-install one wheel**

```bash
package_dir=$(mktemp -d /tmp/scopeproof-runtime-schema-XXXXXX)
'../../.venv/bin/python' -m pip wheel . --no-deps --wheel-dir "$package_dir/dist"
python3 -m venv "$package_dir/venv"
"$package_dir/venv/bin/python" -m pip install --upgrade pip
"$package_dir/venv/bin/python" -m pip install \
  "$package_dir/dist/scopeproof-0.1.17.dev0-py3-none-any.whl"
```

Expected: exactly one ScopeProof wheel is built and installed with declared dependencies.

- [ ] **Step 3: Verify installed identity, dependency consistency, and schema behavior**

Run `pip check`, both console `--version` commands, and a direct installed-package Python probe that:

1. requires distribution metadata, imported `__version__`, and `build_demo_review().review.tool_version` to equal `0.1.17.dev0`;
2. constructs a valid `RuntimeEvidence` and preserves surrounding whitespace exactly;
3. requires whitespace-only `artifact_reference`, `scenario`, `environment`, `result`, and `reviewer` values to raise `ValidationError`;
4. runs `scopeproof benchmark` and requires 12 cases, 13 criteria, zero mismatches, zero must-have False Ready, and zero false blockers.

- [ ] **Step 4: Start the installed web workbench and require exact health**

Start `scopeproof-web` from the clean environment with a temporary `HOME`, host `127.0.0.1`, and an unused port. Require:

```text
GET /_stcore/health -> ok
```

Stop the process and require no shutdown traceback.

### Task 3: Packaged boundary audit and protected integration

**Files:**
- Create audit evidence under `/Users/yjian070/.codex/visualizations/2026/07/14/scopeproof-runtime-evidence-schema-guard/`.

**Interfaces:**
- Consumes: the clean-installed wheel and deliberately constructed demo.
- Produces: current-run screenshots, DOM evidence, audit notes, a ready protected PR, and verified merged main.

- [ ] **Step 1: Recheck the packaged manual-evidence boundary**

Load the demo, explicitly confirm criteria, and run deterministic analysis. Require:

- blank and whitespace-only required fields keep `Save manual runtime evidence` disabled;
- prerequisite and E3/E4 guidance remain visible;
- no runtime record is submitted;
- final acceptance copy still says it does not resolve criteria or override the gate;
- browser diagnostics contain no current packaged-app errors.

Save and inspect each accepted screenshot before using it as evidence.

- [ ] **Step 2: Push and open a ready protected PR**

Push `codex/runtime-evidence-schema-guard`. Open a ready PR describing the reproduced schema gap, unchanged UI and gate boundaries, regression-first proof, source/package/browser verification, and no-cost/no-notification constraints.

- [ ] **Step 3: Merge only after every required check passes**

Wait for both `verify` checks, ScopeProof evidence review, CodeQL language checks, and the aggregate CodeQL result. Fix genuine failures regression-first. Squash-merge only when all required checks pass.

- [ ] **Step 4: Verify merged main and clean up**

Require post-merge main CI and CodeQL success on the merge SHA. Fast-forward local `main`, require `HEAD == origin/main`, remove the owned worktree and branch, and confirm:

- latest public release remains `v0.1.16`;
- no open PRs;
- no open Dependabot, CodeQL, or secret-scanning alerts;
- only SHA-pinned Actions remain;
- local main is clean.
