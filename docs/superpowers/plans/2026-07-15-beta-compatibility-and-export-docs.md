# Beta Compatibility and Export Documentation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this
> plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove ScopeProof's declared Python 3.11 minimum in protected CI and make public export
documentation consistently include the existing HTML format.

**Architecture:** Add a focused Python 3.11 compatibility job ahead of the unchanged Python 3.12
`verify` job, preserving the required check context while avoiding a duplicate Streamlit HTTP smoke.
Lock both the CI minimum and README export inventory with repository contract tests.

**Tech Stack:** GitHub Actions, Python 3.11 and 3.12, Hatchling, pytest, Ruff.

## Global Constraints

- Keep `verify` as the required protected status context.
- Use only `ubuntu-latest` standard GitHub-hosted runners and existing full-SHA Action revisions.
- Do not add dependencies, paid services, billing, private repositories, forks, telemetry, or LLM APIs.
- Do not change evidence, gate, schema, lifecycle, storage, or runtime behavior.
- Do not create a release or claim customer, runtime, correctness, or adoption evidence.

---

### Task 1: Lock the Python minimum and public export inventory

**Files:**
- Modify: `tests/test_repository_contracts.py`

**Interfaces:**
- Consumes: `.github/workflows/ci.yml` and `README.md` as public repository contracts.
- Produces: `test_ci_validates_declared_minimum_python()` and
  `test_readme_documents_all_export_formats()`.

- [ ] **Step 1: Add the failing workflow contract**

Append this test to `tests/test_repository_contracts.py`:

```python
def test_ci_validates_declared_minimum_python() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    compatibility = workflow.split("  compatibility-python-311:", maxsplit=1)[1].split(
        "\n  verify:", maxsplit=1
    )[0]
    verify = workflow.split("\n  verify:", maxsplit=1)[1]

    assert 'python-version: "3.11"' in compatibility
    assert "python -m pytest -q" in compatibility
    assert "python -m scopeproof_core.evals.runner" in compatibility
    assert "python -m pip wheel . --no-deps" in compatibility
    assert "scopeproof --version" in compatibility
    assert "scopeproof-web --version" in compatibility
    assert "needs: compatibility-python-311" in verify
```

- [ ] **Step 2: Add the failing README contract**

Append this independent test:

```python
def test_readme_documents_all_export_formats() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "`.md`, `.json`, `.csv`, or `.html`" in readme
    assert "`json`, `markdown`, `csv`, and `html`" in readme
    assert "Markdown / JSON / CSV / HTML" in readme
    assert "Markdown, JSON, CSV, and HTML exports" in readme
```

- [ ] **Step 3: Verify RED**

Run:

```bash
.venv/bin/python -m pytest \
  tests/test_repository_contracts.py::test_ci_validates_declared_minimum_python \
  tests/test_repository_contracts.py::test_readme_documents_all_export_formats -q
```

Expected: both tests fail because the compatibility job and complete README inventory do not yet
exist. The workflow test may initially fail at the missing split marker; that is the intended
missing-contract failure.

- [ ] **Step 4: Commit the red contracts**

```bash
git add tests/test_repository_contracts.py
git commit -m "test: require minimum Python compatibility evidence"
```

### Task 2: Add the minimum-version compatibility gate

**Files:**
- Modify: `.github/workflows/ci.yml`
- Test: `tests/test_repository_contracts.py`

**Interfaces:**
- Consumes: existing immutable `actions/checkout` and `actions/setup-python` references.
- Produces: job `compatibility-python-311`; existing job `verify` depends on its success.

- [ ] **Step 1: Add the compatibility job before `verify`**

Add this job under `jobs:`:

```yaml
  compatibility-python-311:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0 # v7.0.0
      - uses: actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1 # v6.3.0
        with:
          python-version: "3.11"
          cache: pip
      - name: Upgrade packaging tools
        run: python -m pip install --upgrade pip
      - name: Install
        run: python -m pip install -e '.[dev]'
      - name: Test
        run: python -m pytest -q
      - name: Deterministic benchmark
        run: python -m scopeproof_core.evals.runner
      - name: Installed wheel compatibility smoke
        run: |
          wheel_dir="$RUNNER_TEMP/scopeproof-wheel-python-311"
          python -m pip wheel . --no-deps --wheel-dir "$wheel_dir"
          wheel="$(find "$wheel_dir" -type f -name 'scopeproof-*.whl' -print -quit)"
          python -m pip install --force-reinstall --no-deps "$wheel"
          (cd "$RUNNER_TEMP" && python -c 'from importlib.metadata import version; from scopeproof_core import __version__; assert version("scopeproof") == __version__')
          (cd "$RUNNER_TEMP" && scopeproof --version)
          (cd "$RUNNER_TEMP" && scopeproof-web --version)
```

Add this line directly under the existing `verify:` job id:

```yaml
    needs: compatibility-python-311
```

- [ ] **Step 2: Verify the workflow contract is GREEN**

Run:

```bash
.venv/bin/python -m pytest \
  tests/test_repository_contracts.py::test_ci_validates_declared_minimum_python \
  tests/github_action/test_workflow_files.py -q
```

Expected: all selected tests pass and every Action remains pinned to a 40-character commit SHA.

- [ ] **Step 3: Commit the compatibility gate**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: verify the declared Python minimum"
```

### Task 3: Align the public HTML export documentation

**Files:**
- Modify: `README.md`
- Test: `tests/test_repository_contracts.py`

**Interfaces:**
- Consumes: existing CLI formats `json`, `markdown`, `csv`, and `html`.
- Produces: one consistent public inventory without changing exporter behavior.

- [ ] **Step 1: Document all one-command and repeat-export formats**

After the first `scopeproof review` example, add:

```markdown
The optional report path may end in `.md`, `.json`, `.csv`, or `.html`. ScopeProof validates the
selected export and refuses to overwrite an existing file.
```

After the repeat-export example, add:

```markdown
Available repeat-export formats are `json`, `markdown`, `csv`, and `html`.
```

- [ ] **Step 2: Align architecture and repository-layout copy**

Change the architecture output to:

```text
Markdown / JSON / CSV / HTML
```

Change the reporting layout description to:

```text
scopeproof_core/reporting/Markdown, JSON, CSV, and HTML exports
```

- [ ] **Step 3: Verify the README contract is GREEN**

Run:

```bash
.venv/bin/python -m pytest \
  tests/test_repository_contracts.py::test_readme_documents_all_export_formats -q
```

Expected: one pass.

- [ ] **Step 4: Commit the public documentation**

```bash
git add README.md
git commit -m "docs: expose the complete export inventory"
```

### Task 4: Verify and publish the protected slice

**Files:**
- Verify all modified files and the built package.

**Interfaces:**
- Consumes: the completed repository contracts, CI workflow, and README.
- Produces: one protected PR with no release or external validation claim.

- [ ] **Step 1: Run focused and repository-wide verification**

```bash
.venv/bin/python -m pytest tests/test_repository_contracts.py tests/github_action/test_workflow_files.py -q
.venv/bin/python -m ruff check .
.venv/bin/python -m pytest -q
.venv/bin/python -m scopeproof_core.evals.runner
.venv/bin/python -m pip check
git diff --check main...HEAD
```

Expected: focused contracts pass, Ruff reports `All checks passed!`, the complete offline suite has
zero failures, the benchmark has zero mismatches and zero must-have False Ready, `pip check` reports
no broken requirements, and `git diff --check` is silent.

- [ ] **Step 2: Build and inspect the wheel**

```bash
wheel_dir="$(mktemp -d)"
.venv/bin/python -m pip wheel . --no-deps --wheel-dir "$wheel_dir"
.venv/bin/python -c 'from importlib.metadata import version; from scopeproof_core import __version__; assert version("scopeproof") == __version__'
.venv/bin/scopeproof --version
.venv/bin/scopeproof-web --version
```

Expected: one `scopeproof-0.1.22.dev0-py3-none-any.whl` is built and both CLIs report
`0.1.22.dev0`.

- [ ] **Step 3: Publish through protected GitHub flow**

Push `codex/beta-compat-docs`, open one ready PR, wait for `verify`, `Analyze (python)`, and
`Analyze (actions)`, fix genuine failures, merge only when all checks succeed, and confirm local
`main` equals `origin/main` at the merge commit.

- [ ] **Step 4: Release decision**

Do not publish v0.1.22 for this compatibility/documentation-only slice. Preserve `0.1.22.dev0`
until a verified user-facing change or genuine first-use finding justifies a release.
