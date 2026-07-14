# ScopeProof Action-Evidence GitHub Identity Guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reject Action validation records whose repository identity or GitHub PR/run URLs contain non-slug characters such as whitespace.

**Architecture:** Tighten only the Pydantic field patterns on `ActionValidationRecord`; retain the existing model-level same-repository, marker, rerun, comment-count, and fork checks. The CLI inherits the behavior through its existing model validation call.

**Tech Stack:** Python 3.12, Pydantic 2, pytest, Ruff, argparse CLI

## Global Constraints

- Validation remains offline and never proves a GitHub URL exists.
- Fork testing remains permanently excluded for the single-account public alpha.
- No billing, paid API, organization, second account, private repository, or external comment.
- No Streamlit, lifecycle, finding, gate, runtime-evidence, final-acceptance, export, or storage-version change.

---

### Task 1: Canonical repository and GitHub URL shapes

**Files:**
- Modify: `tests/schemas/test_action_validation_record.py`
- Modify: `scopeproof_core/schemas/models.py`

**Interfaces:**
- Consumes: `ActionValidationRecord.model_validate(data: object) -> ActionValidationRecord`
- Produces: stricter field patterns for `repository`, PR URLs, and Action run URLs

- [ ] **Step 1: Write failing schema tests**

Add parameterized coverage:

```python
@pytest.mark.parametrize(
    ("repository", "url_prefix"),
    [
        (" / ", "https://github.com/ / "),
        ("ac me/de mo", "https://github.com/ac me/de mo"),
        (" acme/demo", "https://github.com/ acme/demo"),
        ("acme/demo\t", "https://github.com/acme/demo\t"),
    ],
)
def test_action_validation_record_rejects_noncanonical_repository_identity(
    repository: str, url_prefix: str
) -> None:
    payload = record_data() | {
        "repository": repository,
        "non_fork_pr_url": f"{url_prefix}/pull/12",
        "non_fork_run_url": f"{url_prefix}/actions/runs/1",
        "rerun_url": f"{url_prefix}/actions/runs/2",
        "fork_pr_url": f"{url_prefix}/pull/13",
        "fork_run_url": f"{url_prefix}/actions/runs/3",
    }

    with pytest.raises(ValueError, match="string_pattern_mismatch"):
        ActionValidationRecord.model_validate(payload)


@pytest.mark.parametrize(
    "field_name",
    [
        "non_fork_pr_url",
        "non_fork_run_url",
        "rerun_url",
        "fork_pr_url",
        "fork_run_url",
    ],
)
def test_action_validation_record_rejects_noncanonical_github_url_field(
    field_name: str,
) -> None:
    payload = record_data()
    suffix = "/pull/12" if field_name.endswith("pr_url") else "/actions/runs/1"
    payload[field_name] = f"https://github.com/ac me/demo{suffix}"

    with pytest.raises(ValueError, match="string_pattern_mismatch"):
        ActionValidationRecord.model_validate(payload)


def test_action_validation_record_accepts_supported_slug_characters() -> None:
    payload = record_data() | {
        "repository": "acme-team/demo.repo_name",
        "non_fork_pr_url": "https://github.com/acme-team/demo.repo_name/pull/12",
        "non_fork_run_url": "https://github.com/acme-team/demo.repo_name/actions/runs/1",
        "rerun_url": "https://github.com/acme-team/demo.repo_name/actions/runs/2",
        "fork_pr_url": "https://github.com/acme-team/demo.repo_name/pull/13",
        "fork_run_url": "https://github.com/acme-team/demo.repo_name/actions/runs/3",
    }

    record = ActionValidationRecord.model_validate(payload)

    assert record.repository == "acme-team/demo.repo_name"
```

- [ ] **Step 2: Run schema tests and verify RED**

Run:

```bash
'../../.venv/bin/python' -m pytest tests/schemas/test_action_validation_record.py -q
```

Expected: malformed repository/URL cases fail because current patterns accept them; the supported
slug-character case passes.

- [ ] **Step 3: Tighten the Pydantic patterns**

Use these exact shapes in `ActionValidationRecord`:

```python
repository: str = Field(pattern=r"^[A-Za-z0-9-]+/[A-Za-z0-9_.-]+$")
non_fork_pr_url: str = Field(
    pattern=r"^https://github\.com/[A-Za-z0-9-]+/[A-Za-z0-9_.-]+/pull/\d+$"
)
non_fork_run_url: str = Field(
    pattern=r"^https://github\.com/[A-Za-z0-9-]+/[A-Za-z0-9_.-]+/actions/runs/\d+$"
)
```

Apply the same PR pattern to `fork_pr_url` and the same run pattern to `rerun_url` and
`fork_run_url`.

- [ ] **Step 4: Run schema tests and verify GREEN**

Run:

```bash
'../../.venv/bin/python' -m pytest tests/schemas/test_action_validation_record.py -q
'../../.venv/bin/python' -m ruff check \
  scopeproof_core/schemas/models.py tests/schemas/test_action_validation_record.py
```

Expected: all schema tests pass and Ruff is clean.

- [ ] **Step 5: Commit the schema slice**

```bash
git add scopeproof_core/schemas/models.py tests/schemas/test_action_validation_record.py
git commit -m "fix: validate Action evidence GitHub identity"
```

---

### Task 2: CLI contract and release-quality verification

**Files:**
- Modify: `tests/cli/test_cli.py`

**Interfaces:**
- Consumes: `scopeproof_core.cli.main(argv: list[str] | None = None) -> int`
- Produces: CLI contract proof that malformed repository identity exits nonzero without validated JSON

- [ ] **Step 1: Add CLI regression coverage**

Add:

```python
def test_action_evidence_command_rejects_noncanonical_repository_identity(
    tmp_path: Path, capsys
) -> None:
    evidence_path = tmp_path / "invalid-repository-action-evidence.json"
    payload = action_evidence_data() | {
        "repository": "ac me/demo",
        "non_fork_pr_url": "https://github.com/ac me/demo/pull/12",
        "non_fork_run_url": "https://github.com/ac me/demo/actions/runs/1",
        "rerun_url": "https://github.com/ac me/demo/actions/runs/2",
        "fork_pr_url": "https://github.com/ac me/demo/pull/13",
        "fork_run_url": "https://github.com/ac me/demo/actions/runs/3",
    }
    evidence_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(SystemExit) as error:
        main(["validate-action-evidence", str(evidence_path)])

    assert error.value.code == 2
    captured = capsys.readouterr()
    assert "string_pattern_mismatch" in captured.err
    assert '"repository"' not in captured.out
```

- [ ] **Step 2: Run focused CLI and schema tests**

Run:

```bash
'../../.venv/bin/python' -m pytest \
  tests/schemas/test_action_validation_record.py tests/cli/test_cli.py -q
'../../.venv/bin/python' -m ruff check \
  scopeproof_core/schemas/models.py \
  tests/schemas/test_action_validation_record.py \
  tests/cli/test_cli.py
```

Expected: focused tests pass and Ruff is clean.

- [ ] **Step 3: Commit CLI coverage**

```bash
git add tests/cli/test_cli.py
git commit -m "test: cover malformed Action repository identity"
```

- [ ] **Step 4: Run complete offline gates**

Run:

```bash
'../../.venv/bin/python' -m ruff check .
'../../.venv/bin/python' -m pytest -q
'../../.venv/bin/python' -m scopeproof_core.cli benchmark
git diff --check main...HEAD
```

Expected: Ruff clean; complete tests pass; the 12-case/13-criterion benchmark reports zero
mismatches, zero must-have False Ready, and zero False Blocker; diff check is clean.

- [ ] **Step 5: Build and smoke a clean-installed wheel**

Build a wheel into a fresh `/tmp` directory using `pip wheel --no-deps`, create a clean virtual
environment, install the wheel, run `pip check`, and exercise:

- one valid Action record, requiring exit `0` and validated JSON;
- one whitespace-containing repository identity, requiring exit `2` and no validated JSON;
- the installed deterministic benchmark, requiring 12 cases, 13 criteria, and all release gates zero.

- [ ] **Step 6: Publish and integrate**

Push `codex/action-evidence-github-identity-guard`, open one focused ready PR, wait for `verify`,
ScopeProof evidence review, and CodeQL, squash-merge only when green, confirm protected-main CI,
synchronize local `main`, and remove the owned worktree/branch after tree-equivalence verification.

Do not publish a release for this schema-only correction. Rotate immediately to the next verified
gap after the post-merge audit.
