# Review Version Provenance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make package builds and newly created ScopeProof reviews derive their version from one checked-in source while preserving historical review provenance.

**Architecture:** Add a small UI-independent version module and configure Hatch's built-in regex version source to read it. The validated `Review` model consumes the same constant, so CLI, Streamlit, persistence, and exports inherit correct provenance without route-specific overrides.

**Tech Stack:** Python 3.11+, Pydantic 2, Hatchling, pytest, Ruff, GitHub Actions.

## Global Constraints

- `scopeproof_core/version.py` is the only checked-in package-version value.
- Existing saved `tool_version` values must be preserved without migration or rewrite.
- Evidence, gate, runtime-evidence, resolution, and final-acceptance semantics remain unchanged.
- The core package must not read repository files or distribution metadata at runtime.
- No dependency, external service, paid API, release, or untrusted-code execution is added.

---

### Task 1: Bind new reviews to one package-version source

**Files:**
- Create: `scopeproof_core/version.py`
- Modify: `scopeproof_core/__init__.py`
- Modify: `scopeproof_core/schemas/models.py:249-261`
- Modify: `pyproject.toml:5-8`
- Test: `tests/schemas/test_models.py`
- Test: `tests/test_repository_contracts.py`

**Interfaces:**
- Produces: `scopeproof_core.version.__version__: str`
- Produces: `scopeproof_core.__version__: str`
- Consumes: `Review.tool_version` default factory and Hatch `[tool.hatch.version]`

- [ ] **Step 1: Write failing schema and repository-contract tests**

In `tests/schemas/test_models.py`, import `__version__` and add:

```python
from scopeproof_core.version import __version__


def test_new_review_records_current_package_version() -> None:
    review = Review(
        repository="acme/repo",
        pr_number=7,
        base_sha="base",
        head_sha="head",
    )
    assert review.tool_version == __version__


def test_review_round_trip_preserves_historical_tool_version() -> None:
    historical = Review(
        repository="acme/repo",
        pr_number=7,
        base_sha="base",
        head_sha="head",
        tool_version="0.1.0",
    )
    reopened = Review.model_validate_json(historical.model_dump_json())
    assert reopened.tool_version == "0.1.0"
```

In `tests/test_repository_contracts.py`, add:

```python
def test_hatch_and_reviews_share_one_version_source() -> None:
    config = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    assert config["project"]["dynamic"] == ["version"]
    assert "version" not in config["project"]
    assert config["tool"]["hatch"]["version"]["path"] == "scopeproof_core/version.py"
```

Remove the obsolete literal-version assertion from
`test_project_exposes_web_launcher_without_coupling_core_to_ui`; the new test owns the contract.

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```bash
../../.venv/bin/python -m pytest \
  tests/schemas/test_models.py::test_new_review_records_current_package_version \
  tests/schemas/test_models.py::test_review_round_trip_preserves_historical_tool_version \
  tests/test_repository_contracts.py::test_hatch_and_reviews_share_one_version_source -q
```

Expected: collection fails because `scopeproof_core.version` does not exist.

- [ ] **Step 3: Add the version source and bind packaging and Review**

Create `scopeproof_core/version.py`:

```python
"""Single checked-in source for ScopeProof package and review provenance."""

__version__ = "0.1.14"
```

Update `scopeproof_core/__init__.py`:

```python
"""ScopeProof's UI-independent evidence engine."""

from scopeproof_core.schemas.models import RULESET_VERSION
from scopeproof_core.version import __version__

__all__ = ["RULESET_VERSION", "__version__"]
```

Import `__version__` in `scopeproof_core/schemas/models.py` and use:

```python
tool_version: str = Field(default_factory=lambda: __version__)
```

Replace the literal version in `pyproject.toml` with:

```toml
dynamic = ["version"]
```

and add:

```toml
[tool.hatch.version]
path = "scopeproof_core/version.py"
```

- [ ] **Step 4: Run focused tests and verify GREEN**

Run the command from Step 2.

Expected: `3 passed`.

- [ ] **Step 5: Run schema, repository, CLI, and Streamlit regressions**

Run:

```bash
../../.venv/bin/python -m pytest \
  tests/schemas/test_models.py tests/test_repository_contracts.py \
  tests/cli/test_cli.py tests/apps/test_streamlit_app.py -q
```

Expected: all selected tests pass.

- [ ] **Step 6: Commit the single-source implementation**

```bash
git add scopeproof_core/version.py scopeproof_core/__init__.py \
  scopeproof_core/schemas/models.py pyproject.toml \
  tests/schemas/test_models.py tests/test_repository_contracts.py
git commit -m "fix: bind reviews to package version"
```

### Task 2: Prove persisted, exported, and installed-wheel provenance

**Files:**
- Modify: `tests/cli/test_cli.py`
- Modify: `.github/workflows/ci.yml`
- Modify: `tests/test_repository_contracts.py`

**Interfaces:**
- Consumes: `scopeproof_core.__version__`, `Review.tool_version`, CLI `review` persistence
- Produces: installed-wheel version smoke and persisted/exported CLI regression evidence

- [ ] **Step 1: Add a CLI provenance assertion**

Import `JsonReviewStore` and `__version__` in `tests/cli/test_cli.py`. Extend
`test_fixture_review_saves_validated_local_record` after locating the saved JSON:

```python
    record = next((tmp_path / "reviews").glob("*.json"))
    state = JsonReviewStore(tmp_path / "reviews").load(record.stem)
    assert state.review.tool_version == __version__
    assert state.bundle is not None
    assert state.bundle.review.tool_version == __version__
```

- [ ] **Step 2: Add installed-wheel version verification to CI**

Immediately after force-installing the wheel in `.github/workflows/ci.yml`, add:

```yaml
          (cd "$RUNNER_TEMP" && python -c '
          from importlib.metadata import version
          from scopeproof_core import __version__
          from scopeproof_core.schemas.models import Review
          review = Review(repository="acme/repo", pr_number=1, base_sha="base", head_sha="head")
          assert version("scopeproof") == __version__ == review.tool_version
          ')
```

- [ ] **Step 3: Add a workflow contract assertion**

Extend `test_ci_builds_and_executes_installed_wheel` with:

```python
    assert 'from scopeproof_core import __version__' in workflow
    assert 'version("scopeproof") == __version__ == review.tool_version' in workflow
```

- [ ] **Step 4: Run focused CLI and workflow tests**

Run:

```bash
../../.venv/bin/python -m pytest \
  tests/cli/test_cli.py::test_fixture_review_saves_validated_local_record \
  tests/test_repository_contracts.py::test_ci_builds_and_executes_installed_wheel -q
```

Expected: `2 passed`.

- [ ] **Step 5: Build and clean-install the wheel locally**

Run:

```bash
rm -rf /tmp/scopeproof-version-wheel /tmp/scopeproof-version-install
mkdir -p /tmp/scopeproof-version-wheel /tmp/scopeproof-version-install
../../.venv/bin/python -m pip wheel . --no-deps --wheel-dir /tmp/scopeproof-version-wheel
../../.venv/bin/python -m pip install --no-deps --target /tmp/scopeproof-version-install \
  /tmp/scopeproof-version-wheel/scopeproof-0.1.14-py3-none-any.whl
PYTHONPATH=/tmp/scopeproof-version-install ../../.venv/bin/python -c '
from importlib.metadata import version
from scopeproof_core import __version__
from scopeproof_core.schemas.models import Review
review = Review(repository="acme/repo", pr_number=1, base_sha="base", head_sha="head")
assert version("scopeproof") == __version__ == review.tool_version == "0.1.14"
'
```

Expected: wheel build and install succeed and the assertion exits zero.

- [ ] **Step 6: Run a real CLI fixture review**

Use a temporary requirements file and storage directory, run `scopeproof_core.cli review`, and
inspect both the persisted record and JSON export. Confirm each validated `review.tool_version` is
`0.1.14`. This is controlled local product evidence, not PR runtime evidence.

- [ ] **Step 7: Commit packaging provenance coverage**

```bash
git add .github/workflows/ci.yml tests/cli/test_cli.py tests/test_repository_contracts.py
git commit -m "ci: verify installed review version"
```

### Task 3: Full verification and protected publication

**Files:**
- Verify: all changed files and built wheel
- Publish: `codex/version-provenance`

**Interfaces:**
- Consumes: completed Tasks 1 and 2
- Produces: protected-main version-provenance correction without a release

- [ ] **Step 1: Run all local gates**

Run:

```bash
../../.venv/bin/python -m ruff check .
../../.venv/bin/python -m pytest -q
../../.venv/bin/python -m scopeproof_core.evals.runner
git diff --check
```

Expected: Ruff passes; all offline tests pass with only the intentional live-network skip; all 12
benchmark cases execute with zero mismatches, zero must-have False Ready, and zero false blockers;
diff check is clean.

- [ ] **Step 2: Review scope and compatibility**

Confirm the diff contains only the version source, packaging binding, review default, provenance
tests, CI smoke, design, and plan. Confirm no old record rewrite, license, dependency, paid service,
gate change, evidence rule, or notification-only file was added.

- [ ] **Step 3: Push once and open one ready protected PR**

Push `codex/version-provenance`, open one ready PR, and wait for required `verify`, CodeQL, and
ScopeProof evidence-review checks. Do not create comments, issues, labels, or a release.

- [ ] **Step 4: Merge and verify protected main**

Merge only when every required check is green. Verify the merge SHA, post-merge main CI and CodeQL,
delete the feature branch, synchronize local main, and continue the persistent goal with the next
evidence-backed slice.
