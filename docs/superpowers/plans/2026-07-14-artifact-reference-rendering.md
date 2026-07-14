# Artifact-Reference Rendering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render only valid absolute HTTP(S) runtime artifact references as links while preserving every other accepted reference as exact, inert text.

**Architecture:** Add one dependency-free reporting helper that classifies linkable references and renders escaped Markdown. Reuse it in Markdown export and Streamlit; make HTML export use the same classifier with HTML escaping. Keep Pydantic validation, persistence, JSON, CSV, lifecycle, and gates unchanged.

**Tech Stack:** Python 3.12, `urllib.parse`, Pydantic 2, Streamlit 1.59, Streamlit AppTest, pytest, Ruff.

## Global Constraints

- Preserve `RuntimeEvidence.artifact_reference` as any nonblank human-supplied string.
- Do not trim, normalize, fetch, probe, execute, or rewrite an artifact reference.
- Link only absolute `http://` or `https://` values with a nonempty network location and no whitespace or angle brackets.
- Render artifact identifiers, local or relative paths, and every non-web scheme as plain text.
- JSON and CSV retain the exact validated value.
- Runtime evidence remains human supplied, append-only, E3/E4-only, and independent from static findings, criterion resolution, final acceptance, and the deterministic gate.
- Do not execute PR code or add a dependency, API, billing, telemetry, generic scanner, auto-fix feature, fork test, release, or notification-generating issue activity.

---

### Task 1: Safe reference rendering in reports

**Files:**
- Create: `scopeproof_core/reporting/references.py`
- Modify: `scopeproof_core/reporting/exporters.py:1-140,320-345`
- Modify: `tests/reporting/test_exporters.py`

**Interfaces:**
- Consumes: `RuntimeEvidence.artifact_reference: str`.
- Produces: `is_linkable_artifact_reference(value: str) -> bool` and `render_artifact_reference_markdown(value: str) -> str`.

- [ ] **Step 1: Add failing report regressions**

Add these tests after the existing export identity tests:

```python
def test_runtime_artifact_identifiers_and_non_web_schemes_are_plain_text() -> None:
    for reference in ("artifact-42", "relative/run-42", "file:///tmp/run-42", "javascript:alert(1)"):
        bundle = example_bundle()
        bundle.runtime_evidence[0].artifact_reference = reference

        markdown_report = export_markdown(bundle)
        html_report = export_html(bundle)

        assert reference in markdown_report
        assert f"[{reference}](" not in markdown_report
        assert reference in html_report
        assert f'href="{reference}"' not in html_report


def test_runtime_http_artifact_reference_remains_clickable() -> None:
    bundle = example_bundle()
    reference = "https://example.test/runs/7?case=(export)"
    bundle.runtime_evidence[0].artifact_reference = reference

    assert f"[{reference}](<{reference}>)" in export_markdown(bundle)
    assert f'<a href="{reference}">{reference}</a>' in export_html(bundle)


def test_runtime_artifact_reference_stays_exact_in_json_and_csv() -> None:
    bundle = example_bundle()
    reference = "artifact-42"
    bundle.runtime_evidence[0].artifact_reference = reference

    assert json.loads(export_json(bundle))["runtime_evidence"][0]["artifact_reference"] == reference
    csv_row = next(csv.DictReader(io.StringIO(export_csv(bundle))))
    assert csv_row["runtime_artifacts"] == reference
```

- [ ] **Step 2: Run the report regressions and verify RED**

Run:

```bash
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m pytest \
  tests/reporting/test_exporters.py::test_runtime_artifact_identifiers_and_non_web_schemes_are_plain_text \
  tests/reporting/test_exporters.py::test_runtime_http_artifact_reference_remains_clickable \
  tests/reporting/test_exporters.py::test_runtime_artifact_reference_stays_exact_in_json_and_csv -q
```

Expected: the first test fails because all values receive links; the HTTP test fails because the
Markdown destination is not angle-delimited; the JSON/CSV preservation test already passes and
guards the unchanged data contract.

- [ ] **Step 3: Create the focused reference helper**

Create `scopeproof_core/reporting/references.py`:

```python
"""Render human-supplied artifact references without inventing unsafe links."""

from __future__ import annotations

from urllib.parse import urlsplit


def is_linkable_artifact_reference(value: str) -> bool:
    """Return whether an artifact reference is a safe absolute web URL."""
    if any(character.isspace() for character in value) or "<" in value or ">" in value:
        return False
    try:
        parsed = urlsplit(value)
    except ValueError:
        return False
    return parsed.scheme.lower() in {"http", "https"} and bool(parsed.netloc)


def _escape_markdown_text(value: str) -> str:
    escaped = value.replace("\\", "\\\\")
    for character in ("`", "*", "_", "[", "]", "<", ">"):
        escaped = escaped.replace(character, f"\\{character}")
    return escaped


def render_artifact_reference_markdown(value: str) -> str:
    """Return a Markdown link for HTTP(S), otherwise escaped plain text."""
    label = _escape_markdown_text(value)
    if not is_linkable_artifact_reference(value):
        return label
    return f"[{label}](<{value}>)"
```

- [ ] **Step 4: Use the helper in Markdown and HTML exports**

Import both public helper functions in `scopeproof_core/reporting/exporters.py`. Replace the runtime
Markdown reference with:

```python
f"- **{item.criterion_id}** — "
f"{render_artifact_reference_markdown(item.artifact_reference)}"
```

Add this private HTML adapter near the other exporter helpers:

```python
def _render_artifact_reference_html(value: str) -> str:
    label = html.escape(value)
    if not is_linkable_artifact_reference(value):
        return label
    return f'<a href="{html.escape(value, quote=True)}">{label}</a>'
```

Replace the unconditional runtime-evidence anchor with
`_render_artifact_reference_html(item.artifact_reference)`.

- [ ] **Step 5: Run the report regressions and verify GREEN**

Run the Step 2 command. Expected: `3 passed`.

- [ ] **Step 6: Run reporting checks and commit**

```bash
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m pytest tests/reporting -q
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m ruff check \
  scopeproof_core/reporting/references.py scopeproof_core/reporting/exporters.py \
  tests/reporting/test_exporters.py
git diff --check
git add scopeproof_core/reporting/references.py scopeproof_core/reporting/exporters.py \
  tests/reporting/test_exporters.py
git commit -m "fix: render artifact references safely"
```

Expected: all reporting tests and Ruff pass; the commit contains only the helper, report adapters,
and report regressions.

### Task 2: Safe reference rendering in Streamlit

**Files:**
- Modify: `apps/web/app.py:1-35,735-750`
- Modify: `tests/apps/test_streamlit_app.py`

**Interfaces:**
- Consumes: `render_artifact_reference_markdown(value: str) -> str` from Task 1.
- Produces: one Streamlit Markdown row whose artifact reference is clickable only for HTTP(S).

- [ ] **Step 1: Add a failing AppTest regression**

Add this test after `test_manual_runtime_evidence_can_be_recorded_without_changing_static_findings`:

```python
def test_runtime_artifact_identifier_renders_as_plain_text() -> None:
    app = analyzed_demo(new_app())
    app = app.text_input(key="runtime_artifact_reference").set_value("artifact-42").run()
    app = app.text_area(key="runtime_scenario").set_value("Fixture scenario").run()
    app = app.text_input(key="runtime_environment").set_value("Fixture environment").run()
    app = app.text_input(key="runtime_result").set_value("Fixture result").run()
    app = app.text_input(key="runtime_reviewer").set_value("Fixture reviewer").run()
    app = app.button(key="save_runtime_evidence").click().run()

    runtime_rows = [item.value for item in app.markdown if "artifact-42" in item.value]
    assert runtime_rows == [
        "- artifact-42 — Fixture scenario (Fixture environment: Fixture result; E3)"
    ]
```

This fixture verifies presentation behavior only and must not be described as real PR runtime
evidence or external validation.

- [ ] **Step 2: Run the AppTest and verify RED**

```bash
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m pytest \
  tests/apps/test_streamlit_app.py::test_runtime_artifact_identifier_renders_as_plain_text -q
```

Expected: FAIL because the row contains `[artifact-42](artifact-42)`.

- [ ] **Step 3: Reuse the Markdown helper in the workbench**

Import `render_artifact_reference_markdown` from
`scopeproof_core.reporting.references`. Replace the selected runtime row with:

```python
        artifact_reference = render_artifact_reference_markdown(item.artifact_reference)
        st.markdown(
            f"- {artifact_reference} — {item.scenario} "
            f"({item.environment}: {item.result}; {item.evidence_level.value})"
        )
```

- [ ] **Step 4: Run the AppTest and verify GREEN**

Run the Step 2 command. Expected: `1 passed`.

- [ ] **Step 5: Run focused UI and boundary checks**

```bash
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m pytest \
  tests/apps/test_streamlit_app.py tests/reporting -q
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m ruff check \
  apps/web/app.py tests/apps/test_streamlit_app.py
git diff --check
```

Expected: all Streamlit and reporting tests pass with unchanged runtime-evidence readiness, reset,
criterion-resolution, final-acceptance, and gate behavior.

- [ ] **Step 6: Commit the UI integration**

```bash
git add apps/web/app.py tests/apps/test_streamlit_app.py
git commit -m "fix: show artifact IDs as plain text"
```

### Task 3: Full verification and protected integration

**Files:** Verify only.

**Interfaces:**
- Consumes: committed Task 1 and Task 2 behavior.
- Produces: source, package, browser, protected-PR, and exact-main evidence.

- [ ] **Step 1: Run repository-wide verification**

```bash
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m ruff check .
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m pytest -q
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m scopeproof_core.evals.runner
git diff --check
```

Expected: Ruff passes; at least 432 tests pass with only the intentional live GitHub test skipped;
all 12 benchmark cases execute with zero mismatches, zero must-have False Ready, and zero false
blockers.

- [ ] **Step 2: Build and clean-install the wheel**

Build `scopeproof-0.1.18.dev0-py3-none-any.whl` into a fresh `/tmp` directory, install it with
declared dependencies into a fresh virtual environment, run `pip check`, verify distribution,
imported, CLI, web CLI, and new-review versions all equal `0.1.18.dev0`, run the installed benchmark
outside the checkout, start installed `scopeproof-web` on loopback, and require exact health `ok`.
Record the wheel SHA-256; do not publish or attach it.

- [ ] **Step 3: Run the source-bound browser acceptance check**

Use the repaired editable console entry point and a temporary `HOME`. Load the deliberately
constructed demo, confirm criteria, and run analysis. Confirm the current artifact-or-URL label,
runtime boundary, disabled empty save action, criterion resolution, and final-acceptance boundary.
Do not submit a runtime record, resolution, or final acceptance. Use AppTest and export regressions
for the post-save artifact-ID transition, and retain the accepted empty-form screenshot as product
evidence only.

- [ ] **Step 4: Request a read-only code review**

Provide the exact base and head SHAs, this plan, the design, and verification evidence to an
independent reviewer. Fix every Critical or Important issue before publication.

- [ ] **Step 5: Publish one protected PR**

Push `codex/artifact-reference-rendering` and open one ready PR against `main`. Add no reviewers,
comments, issue updates, release activity, or other notification-generating writes. Wait for
required `verify`, ScopeProof, and CodeQL checks and merge only when all are green.

- [ ] **Step 6: Verify exact merged main and clean up**

Require merged-main CI and both CodeQL analyses to succeed at the exact merge SHA. Fast-forward
local `main`, remove the owned worktree and local/remote feature branch, prune worktrees, and confirm
`HEAD == origin/main`, zero open PRs, zero open Dependabot/CodeQL/secret-scanning alerts, repository
notifications still ignored, and a clean checkout. Keep v0.1.17 as the latest public release and
rotate the continuous goal to the next verified gap.
