# Export Provenance Consistency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Markdown, CSV, HTML, and JSON exports all identify the exact ScopeProof tool and ruleset versions that produced the review.

**Architecture:** Read provenance only from the validated `bundle.review` already consumed by every exporter. Add format-native fields directly to the three incomplete renderers; JSON remains unchanged because model serialization already includes both versions.

**Tech Stack:** Python 3.11+, Pydantic 2, csv, HTML escaping, pytest, Ruff.

## Global Constraints

- Every export contains both `Review.tool_version` and `Review.ruleset_version`.
- Historical saved values are preserved; exporters never substitute the installed version.
- HTML provenance values are escaped through `html.escape`.
- No schema, gate, evidence, runtime-evidence, persistence, dependency, or release change is added.

---

### Task 1: Add failing cross-format provenance contracts

**Files:**
- Modify: `tests/reporting/test_exporters.py`
- Modify: `tests/reporting/test_html_export.py`

**Interfaces:**
- Consumes: `example_bundle() -> ReviewBundle`, `build_demo_review() -> ReviewBundle`
- Produces: exact provenance requirements for Markdown, CSV, HTML, and JSON

- [ ] **Step 1: Require tool and ruleset values across all formats**

Add to `tests/reporting/test_exporters.py`:

```python
def test_exports_preserve_tool_and_ruleset_provenance() -> None:
    bundle = example_bundle()

    for output in (
        export_json(bundle),
        export_markdown(bundle),
        export_csv(bundle),
        export_html(bundle),
    ):
        assert bundle.review.tool_version in output
        assert bundle.review.ruleset_version in output
```

Extend the CSV row test:

```python
    bundle = example_bundle()
    rows = list(csv.DictReader(io.StringIO(export_csv(bundle))))
    assert rows[0]["tool_version"] == bundle.review.tool_version
    assert rows[0]["ruleset_version"] == bundle.review.ruleset_version
```

- [ ] **Step 2: Prove historical provenance and HTML escaping**

Add:

```python
def test_human_readable_exports_keep_historical_tool_version() -> None:
    bundle = example_bundle()
    bundle.review.tool_version = "0.1.0"

    for output in (export_markdown(bundle), export_csv(bundle), export_html(bundle)):
        assert "0.1.0" in output
```

In `tests/reporting/test_html_export.py`, add:

```python
def test_html_export_escapes_review_provenance() -> None:
    bundle = build_demo_review()
    bundle.review.tool_version = "dev<unsafe>"
    bundle.review.ruleset_version = "rules<unsafe>"

    html = export_html(bundle)
    assert "dev&lt;unsafe&gt;" in html
    assert "rules&lt;unsafe&gt;" in html
    assert "dev<unsafe>" not in html
```

- [ ] **Step 3: Run the new tests and verify RED**

Run:

```bash
../../.venv/bin/python -m pytest \
  tests/reporting/test_exporters.py::test_exports_preserve_tool_and_ruleset_provenance \
  tests/reporting/test_exporters.py::test_human_readable_exports_keep_historical_tool_version \
  tests/reporting/test_html_export.py::test_html_export_escapes_review_provenance -q
```

Expected: failures show Markdown and CSV lack tool version and HTML lacks both values.

- [ ] **Step 4: Commit the RED tests**

```bash
git add tests/reporting/test_exporters.py tests/reporting/test_html_export.py
git commit -m "test: cover export version provenance"
```

### Task 2: Render validated provenance in each incomplete format

**Files:**
- Modify: `scopeproof_core/reporting/exporters.py`
- Test: `tests/reporting/test_exporters.py`
- Test: `tests/reporting/test_html_export.py`

**Interfaces:**
- Consumes: `Review.tool_version: str`, `Review.ruleset_version: str`
- Produces: additive Markdown line, CSV column, and escaped HTML identity text

- [ ] **Step 1: Add Markdown tool identity**

In the Markdown header list, insert after Head SHA:

```python
        f"**Tool version:** `{bundle.review.tool_version}`",
```

Keep the existing Ruleset line unchanged.

- [ ] **Step 2: Add CSV tool identity**

Insert `"tool_version"` immediately before `"ruleset_version"` in `fieldnames`, and add to each
row:

```python
                "tool_version": bundle.review.tool_version,
```

- [ ] **Step 3: Add escaped HTML identity**

Extend the existing repository/PR/head/revision paragraph with:

```python
            f"Tool <code>{html.escape(bundle.review.tool_version)}</code> · "
            f"Ruleset <code>{html.escape(bundle.review.ruleset_version)}</code> · "
```

- [ ] **Step 4: Run focused tests and verify GREEN**

Run the Task 1 Step 3 command.

Expected: `3 passed`.

- [ ] **Step 5: Run all reporting regressions and Ruff**

Run:

```bash
../../.venv/bin/python -m pytest tests/reporting -q
../../.venv/bin/python -m ruff check \
  scopeproof_core/reporting/exporters.py tests/reporting/test_exporters.py \
  tests/reporting/test_html_export.py
```

Expected: all reporting tests and Ruff pass.

- [ ] **Step 6: Commit implementation**

```bash
git add scopeproof_core/reporting/exporters.py
git commit -m "fix: include provenance in every export"
```

### Task 3: Verify real CLI exports and publish

**Files:**
- Verify: complete repository and four CLI export formats
- Publish: `codex/export-provenance`

**Interfaces:**
- Consumes: a validated local fixture review and existing CLI exporters
- Produces: protected-main export provenance consistency without a release

- [ ] **Step 1: Run a real four-format CLI export**

Create a temporary local fixture review, then run `scopeproof export` for JSON, Markdown, CSV, and
HTML. Verify each file contains `0.1.15.dev0` and `1.0.0`. Treat this as controlled local product
evidence, not external PR runtime evidence.

- [ ] **Step 2: Run all repository gates**

Run Ruff, the full offline pytest suite, the 12-case deterministic benchmark, and
`git diff --check`.

Expected: zero lint/test failures, only the intentional live-network skip, zero benchmark
mismatches, zero must-have False Ready, and zero false blockers.

- [ ] **Step 3: Review compatibility and scope**

Confirm changes are additive export metadata only. Confirm historical values remain intact, HTML
escapes them, and no schema, gate, evidence, runtime-evidence, dependency, release, billing,
license, fork, or external write was added.

- [ ] **Step 4: Publish through one protected PR**

Push once, open one ready PR, wait for `verify`, CodeQL, and ScopeProof evidence review, and merge
only when green. Do not create a release, issue, comment, or label.

- [ ] **Step 5: Verify main and continue**

Verify the merge SHA and post-merge CI/CodeQL, clean the worktree and branches, synchronize local
main, and continue the persistent goal with the next evidence-backed gap.
