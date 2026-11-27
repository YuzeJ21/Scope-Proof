# Workbench CI Comparison Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Integrate the reviewed CI handoff changes and let workbench reviewers export the
same validated CI comparison without using the CLI.

**Architecture:** Reuse the existing core and HTML exporter. Add one focused workbench
module; bind its deferred output to both immutable inputs and existing review authority.

**Tech Stack:** Existing Python, Pydantic, Streamlit, pytest/AppTest and Playwright.

**Spec:** `docs/superpowers/specs/2026-11-27-workbench-ci-comparison-design.md`

## Global Constraints

- Both inputs are at most 1 MiB and match the same confirmed criteria and exact reviewed head.
- Previous/current reflect supplied order; gate and acceptance stay recorded facts.
- Preserve input/saved bytes, frozen examples and R-002; add no dependency or record schema.
- No package/Pages publication or participant contact.

## Review Focus

- A configured input changes while a callback renders: deny the output.
- A previous upload is replaced or removed: deny the earlier callback.
- A current upload replaces a configured source: do not mix the source identities.
- A pending draft or source conflict appears: existing deferred guards still apply.
- Reopening another review or changing the saved record: deny the captured comparison.

### Task 1: Preserve byte identity in configured CI reads

**Files:** `scopeproof_core/reviews/ci_handoff.py`, `tests/reviews/test_ci_manifest_handoff.py`.

**Interfaces:** Produce `load_exact_ci_manifest_with_payload(directory: Path,
bundle: ReviewBundle) -> tuple[CIStatusManifest, bytes]`; preserve the existing wrappers.

- [x] Add a failing regression for exact payload bytes, including newline variations.
- [x] Run it and observe missing interface failure.
- [x] Implement the bounded reader and delegate the existing digest/model APIs to it.
- [x] Run the complete CI handoff tests and commit.

### Task 2: Workbench comparison and guarded download

**Files:** Create `apps/web/ci_comparison.py`, `tests/apps/test_ci_comparison.py`;
modify `apps/web/ci_status.py` and existing tests only where behavior requires it.

**Interfaces:** Consume the byte reader, `compare_ci_status`, existing HTML exporter and
`prepare_download: Callable[[ExportRenderer], Callable[[], str]]`. Produce
`render_ci_comparison(...) -> None` and `retire_ci_comparison_download() -> None`.

- [x] Add failing AppTest/callback regressions for opt-in, literal B transitions, validation,
  input identity, retirement and all Review Focus conditions.
- [x] Observe intended failures, then implement the optional previous uploader and tables.
- [x] Guard download before/after rendering; rebuild using the authoritative bundle.
- [x] Run CI panel, handoff, comparison and deferred-export regressions; commit.

### Task 3: Installed workflow, roadmap and integration

**Files:** Add `tests/browser/test_workbench_ci_comparison.py`; update Windows CI wiring,
evaluation guide, changelog, roadmap and an audit note.

**Interfaces:** Use the real installed workbench and existing browser download helpers;
no new application interface.

- [x] Add installed-browser regression for explicit selection, downloaded offline report,
  wrong previous input and unchanged saved record.
- [x] Document the command/UI outcome and accurate next-stage boundaries.
- [x] Run relevant source suite, Ruff, whitespace and frozen-artifact checks.
- [x] Obtain one fresh branch review, fix important findings with RED/GREEN regressions.
- [ ] Sync an exact-tree PR, pass full hosted CI, merge authorized verified work, and verify main.
