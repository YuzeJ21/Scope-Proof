# Accessibility and platform evidence implementation plan

> Execute continuously on `codex/accessibility-platform-evidence`. Do not merge, release, tag,
> begin outreach, generate R-003, retune R-002, or claim Stage 1 progress.

**Goal:** Add durable installed-wheel keyboard/focus evidence and genuine Python 3.13 compatibility
evidence while recording native zoom and unsupported environments without overclaiming.

**Architecture:** Keep product and gate code unchanged unless a reproduced defect requires a
test-first repair. Extend the packaged Playwright boundary for keyboard interaction, add an
isolated Python 3.13 CI compatibility job, and update evidence documents only from observed runs.

---

## Task 1: Establish the bounded environment evidence

- Verify branch, base, status, GitHub authentication, checks, available browsers, Python
  interpreters, VoiceOver availability, and absent Windows/Linux desktop environments.
- Run the constructed primary path in real Chrome at native 200% zoom using keyboard input.
- Require Chrome's visible 200% indicator plus matching pixel-ratio/viewport metrics, inspect
  horizontal control clipping, and restore 100% zoom.
- Attempt VoiceOver only through a bounded observable control path. If no trustworthy state is
  exposed, record the exact limitation and stop that probe.

## Task 2: Replace partial keyboard evidence with a durable regression

**File:** `tests/browser/test_packaged_workbench.py`

- Add a helper that reaches a locator with page-level Tab presses only.
- Assert the active target is enabled, intersects the viewport, and has visible focus styling.
- Open the demo disclosure and activate Load, Confirm, and Run using keyboard input only.
- Enter the reviewer field through the keyboard path.
- Preserve the existing installed-wheel, isolated-home, network, error, viewport, content, export,
  and teardown assertions.
- Run the focused packaged-browser test. If it exposes a product defect, preserve the failing test,
  apply the narrowest repair, and rerun it.

## Task 3: Add genuine Python 3.13 compatibility coverage

**File:** `.github/workflows/ci.yml`

- Add a separate `compatibility-python-313` job without renaming existing protected jobs.
- Install on CPython 3.13, run the complete suite and both deterministic benchmarks, build and
  reinstall the wheel, check imports and both versioned entry points, rerun both installed
  benchmarks, launch the installed workbench on loopback, require exact health `ok`, and clean up.
- Make `verify` depend on the new compatibility job.
- Obtain a genuine managed local CPython 3.13 interpreter and repeat the package, CLI, health, and
  deterministic-gate checks locally.

## Task 4: Update exact evidence documents

**Files:**

- `docs/audits/accessibility-platform-evidence/verification.md`
- `docs/releases/v0.2.3-status-and-next-stages.md`

- Record the exact tested host, Chrome zoom signals, keyboard path, focus assertions, Python 3.13
  interpreter, commands, and results.
- Classify VoiceOver as unsupported unless observable screen-reader evidence was obtained.
- Keep Windows and Linux desktop unsupported; distinguish the Linux headless CI job.
- Preserve every trust boundary and the exact Stage 1 zero counts.

## Task 5: Run full verification

- Run Ruff.
- Run the complete suite with combined coverage at or above 95%.
- Run repository contracts and both deterministic benchmarks.
- Build the wheel twice and require matching SHA-256 values.
- Install the final wheel into fresh Python 3.12 and 3.13 environments; run `pip check`, package
  imports, both version commands, both benchmarks, and exact loopback health.
- Run the installed-wheel browser regression with the pinned Playwright driver.
- Check distribution inventory, `git diff --check`, status, and preservation of `.coverage 2`.

## Task 6: Publish for owner review

- Stage named files only and commit intentionally.
- Push the feature branch and open a ready-for-review PR against `main`.
- Monitor CI, CodeQL, and review feedback to completion.
- Diagnose failures systematically; fix only confirmed in-scope defects with regression coverage.
- Recheck the final diff, commits, mergeability, exact head, check conclusions, unsupported
  environments, and owner decision required.
