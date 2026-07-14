# Review Identity Guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reject blank or malformed public-PR identity before ScopeProof persists or exports a review.

**Architecture:** Keep identity validation in the existing Pydantic models. Reuse one canonical GitHub repository pattern across Action, snapshot, and review records, and apply matching nonblank SHA validators at both ingestion and persisted-review boundaries. Exporters, storage, lifecycle, evidence, and gates remain consumers of already validated objects.

**Tech Stack:** Python 3.12, Pydantic v2, pytest, Ruff, existing local JSON store and exporters.

## Global Constraints

- No paid or hosted API, LLM, billing, organization, second account, private repository, or fork testing.
- Never execute untrusted PR code or invent evidence, users, requirements, findings, or validation.
- Preserve deterministic gates, False Ready safety, final acceptance, evidence levels, and local-first behavior.
- Keep the core engine independent from Streamlit and GitHub UI layers.
- Valid non-40-character fixture and historical SHA identifiers remain supported.
- Reject invalid identity without trimming or normalizing valid input.
- Do not publish a release solely for this schema hardening slice.

---

### Task 1: Guard snapshot and review identity

**Files:**
- Modify: `tests/schemas/test_models.py`
- Modify: `scopeproof_core/schemas/models.py`

**Interfaces:**
- Consumes: `PullRequestSnapshot.model_validate(payload)` and `Review.model_validate(payload)`.
- Produces: consistent repository-pattern validation and nonblank `base_sha` / `head_sha` validation in both models.

- [ ] **Step 1: Add the failing schema tests**

Add this helper and focused tests to `tests/schemas/test_models.py`:

```python
def review_identity_payload(model, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "repository": "acme/widgets",
        "pr_number": 7,
        "base_sha": "base123",
        "head_sha": "head123",
    }
    if model is PullRequestSnapshot:
        payload.update(
            {
                "title": "Example",
                "html_url": "https://github.com/acme/widgets/pull/7",
            }
        )
    payload.update(overrides)
    return payload


@pytest.mark.parametrize("model", [PullRequestSnapshot, Review])
@pytest.mark.parametrize("field_name", ["base_sha", "head_sha"])
@pytest.mark.parametrize("blank", ["   ", "\t\n"])
def test_review_identity_rejects_whitespace_only_shas(model, field_name, blank) -> None:
    with pytest.raises(
        ValidationError, match="review identity must contain non-whitespace text"
    ):
        model.model_validate(review_identity_payload(model, **{field_name: blank}))


@pytest.mark.parametrize("model", [PullRequestSnapshot, Review])
@pytest.mark.parametrize("repository", [" / ", "acme/ ", " acme/widgets", "acme/widgets/extra"])
def test_review_identity_rejects_malformed_repositories(model, repository) -> None:
    with pytest.raises(ValidationError):
        model.model_validate(review_identity_payload(model, repository=repository))


@pytest.mark.parametrize("model", [PullRequestSnapshot, Review])
def test_review_identity_preserves_valid_nonblank_values(model) -> None:
    payload = review_identity_payload(
        model,
        repository="YuzeJ21/Scope-Proof",
        base_sha="  base123  ",
        head_sha="head-demo-002",
    )

    identity = model.model_validate(payload)

    assert identity.repository == "YuzeJ21/Scope-Proof"
    assert identity.base_sha == "  base123  "
    assert identity.head_sha == "head-demo-002"
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```bash
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m pytest \
  tests/schemas/test_models.py::test_review_identity_rejects_whitespace_only_shas \
  tests/schemas/test_models.py::test_review_identity_rejects_malformed_repositories \
  tests/schemas/test_models.py::test_review_identity_preserves_valid_nonblank_values -q
```

Expected: whitespace-only SHA and malformed repository cases fail because the current models accept them; valid preservation cases pass.

- [ ] **Step 3: Implement the minimal shared validation**

In `scopeproof_core/schemas/models.py`, define one constant near `RULESET_VERSION`:

```python
GITHUB_REPOSITORY_PATTERN = r"^[A-Za-z0-9-]+/[A-Za-z0-9_.-]+$"
```

Use it for `ActionValidationRecord.repository`, `PullRequestSnapshot.repository`, and `Review.repository`. Add the following validator independently to `PullRequestSnapshot` and `Review` so both boundaries return their own validated model:

```python
@field_validator("base_sha", "head_sha")
@classmethod
def require_non_blank_review_identity(cls, value: str) -> str:
    if not value.strip():
        raise ValueError("review identity must contain non-whitespace text")
    return value
```

- [ ] **Step 4: Run the focused tests and verify GREEN**

Run the command from Step 2.

Expected: all parametrized identity cases pass with no warnings.

- [ ] **Step 5: Run nearby schema regressions**

Run:

```bash
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m pytest \
  tests/schemas/test_models.py tests/schemas/test_action_validation_record.py -q
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m ruff check \
  scopeproof_core/schemas/models.py tests/schemas/test_models.py
```

Expected: all tests pass and Ruff reports no errors.

### Task 2: Prove bundle and exporter protection

**Files:**
- Modify: `tests/schemas/test_review_bundle_integrity.py`

**Interfaces:**
- Consumes: `ReviewBundle.model_validate(payload)` with nested persisted review identity.
- Produces: a regression proving invalid nested identity is rejected before JSON, Markdown, CSV, or HTML exporters receive a bundle.

- [ ] **Step 1: Add the bundle regression**

Add this test to `tests/schemas/test_review_bundle_integrity.py`:

```python
@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("repository", " / "),
        ("base_sha", "   "),
        ("head_sha", "\t"),
    ],
)
def test_review_bundle_integrity_rejects_invalid_review_identity(
    field_name: str, invalid_value: str
) -> None:
    payload = bundle_payload()
    payload["review"][field_name] = invalid_value

    with pytest.raises(ValidationError):
        ReviewBundle.model_validate(payload)
```

- [ ] **Step 2: Run the regression and verify GREEN through the new nested boundary**

Run:

```bash
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m pytest \
  tests/schemas/test_review_bundle_integrity.py::test_review_bundle_integrity_rejects_invalid_review_identity -q
```

Expected: all three cases pass because the nested `Review` now rejects invalid identity.

- [ ] **Step 3: Run all schema, storage, and exporter tests**

Run:

```bash
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m pytest \
  tests/schemas tests/storage tests/reporting -q
```

Expected: all tests pass, including historical review round trips and every export format.

### Task 3: Verify, commit, and prepare protected publication

**Files:**
- Verify all changed files.

**Interfaces:**
- Consumes: the completed schema and regression changes.
- Produces: one reviewed commit ready for the protected pull-request workflow.

- [ ] **Step 1: Run repository-wide verification**

Run:

```bash
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m ruff check .
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m pytest -q
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m scopeproof_core.evals.runner
git diff --check
```

Expected: Ruff passes; all tests pass; the benchmark executes 12 cases with zero mismatches, zero must-have False Ready, and zero false blockers; the diff is clean.

- [ ] **Step 2: Build and smoke-test a clean wheel outside the checkout**

Run:

```bash
rm -rf /tmp/scopeproof-review-identity-wheel /tmp/scopeproof-review-identity-venv
mkdir -p /tmp/scopeproof-review-identity-wheel
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m pip wheel . --no-deps \
  --wheel-dir /tmp/scopeproof-review-identity-wheel
python3 -m venv /tmp/scopeproof-review-identity-venv
/tmp/scopeproof-review-identity-venv/bin/python -m pip install --upgrade pip
/tmp/scopeproof-review-identity-venv/bin/python -m pip install \
  /tmp/scopeproof-review-identity-wheel/scopeproof-*.whl
/tmp/scopeproof-review-identity-venv/bin/python -m pip check
(cd /tmp && /tmp/scopeproof-review-identity-venv/bin/scopeproof --version)
(cd /tmp && /tmp/scopeproof-review-identity-venv/bin/scopeproof benchmark)
```

Expected: the wheel builds and installs cleanly; `pip check` passes; CLI version is `0.1.18.dev0`; installed benchmark reports the same 12-case zero-mismatch safety results.

- [ ] **Step 3: Verify the installed local workbench health endpoint**

Run the installed `scopeproof-web` on `127.0.0.1:8514`, poll `/_stcore/health` until it returns exactly `ok`, then stop the process. Do not submit any review, evidence, resolution, or final acceptance.

Expected: the installed workbench becomes healthy and exits cleanly after the smoke check.

- [ ] **Step 4: Review and commit the implementation**

Run:

```bash
git status --short
git diff --stat
git diff --check
git add scopeproof_core/schemas/models.py \
  tests/schemas/test_models.py \
  tests/schemas/test_review_bundle_integrity.py \
  docs/superpowers/plans/2026-07-14-review-identity-guard.md
git commit -m "fix: validate review identity context"
```

Expected: one intentional implementation commit after the earlier design commit, with no unrelated files.
