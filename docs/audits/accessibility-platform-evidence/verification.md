# Accessibility and platform evidence verification

> **Historical evidence boundary:** This audit remains bound to its named commit, tree, version,
> and environment. The [current status](../../releases/v0.2.3-status-and-next-stages.md) supersedes
> unqualified present-state inferences and does not rewrite the results below.

## Evidence boundary

- Date: 2026-08-09 (America/Toronto).
- Branch: `codex/accessibility-platform-evidence`.
- Final executable/test verification HEAD: `1a3defcfec5f9f2231a67e8f0a4450d43a63b9b4`
  with tree `b01e358b5aefefd7eaf8abf28e0bf7502cf962af`.
- Base: `origin/main` at `30177733ef312ced22e6a2e57e3df6fdb1e92507`.
- Host: macOS 26.5.1 build 25F80 on Apple silicon.

This is engineering evidence for ScopeProof's own installed workflow. It does not establish WCAG
conformance, correctness, target-repository runtime behavior, authenticated reviewer authority,
customer use, production use, accessibility by every user, or broad platform support. It does not
advance Stage 1.

The canonical Stage 1 counts remain:

- 0/5 qualifying reviews;
- 0/3 independent practitioners;
- 0/3 public repositories;
- 0/3 independently observed under-ten-minute completions;
- 0/2 reuse-intent signals.

## Implemented evidence slice

- The installed-wheel Playwright regression now reaches the complete constructed primary path
  with page-level Tab navigation, keyboard typing, Enter, and Space only. It no longer clicks the
  demo disclosure or moves focus programmatically.
- The regression requires the demo disclosure, demo-load button, reviewer input, criteria-confirm
  button, and deterministic-analysis button to be enabled and intersect the viewport. It compares
  unfocused and focused computed styles and requires a changed, nontransparent outline or shadow,
  so always-on decoration and transparent focus styling cannot satisfy the assertion.
- Existing 1280-by-720 and 390-by-844 contexts, isolated temporary home, loopback-only network
  guard, browser-error assertions, evidence content, export controls, width checks, and process
  cleanup remain in force.
- CI now has a separate `compatibility-python-313` job. It does not rename the existing Python
  3.11 or `verify` jobs. The new job runs the complete suite, both deterministic benchmarks, wheel
  build/reinstallation, `pip check`, both CLI version commands, installed benchmarks, and exact
  loopback workbench health on CPython 3.13. `verify` depends on the new job.
- ScopeProof product and deterministic-gate source code did not change in this slice.

## Keyboard-only installed-wheel evidence

Command:

```text
uv run pytest -q -m browser tests/browser/test_packaged_workbench.py
```

Result on the final executable/test verification tree: `3 passed in 26.11s`. This includes the
full installed-wheel browser journey plus pure regressions proving that unchanged always-on
decoration is rejected and a changed visible outline is accepted. The complete suite on the same
tree passed with `1,956 passed, 2 skipped` and 95.06% combined coverage. The hosted `verify` job
also passed the packaged browser regression on this exact head.

Earlier in the slice, the first new journey run failed because the helper required the Confirm
button to be enabled before Tab blurred and committed the reviewer input. The DOM already
contained the full reviewer value. Moving the enabled assertion to the point where keyboard focus
actually reaches the target fixed that ordering defect. A subsequent independent review found
that the original focus predicate could accept unchanged or transparent decoration; the final
helper and the two pure regressions above close that false-pass path. No ScopeProof product change
was required for either repair.

The final regression repeated the full path in fresh 1280-by-720 and 390-by-844 contexts. It
opened `Try ScopeProof`, loaded the deliberately constructed demo, entered the asserted reviewer
label, confirmed normalized criteria, and ran deterministic analysis without pointer input or
programmatic focus. Every primary target met the visible-focus and in-viewport assertions. The
matrix retained missing-evidence guidance, the summary remained fail-closed at `Action required`,
and Markdown, JSON, and CSV controls were visible and enabled. The final browser and external-
request lists were empty.

This proves the tested primary path. It does not prove every control or all possible tab orders.

## Actual 200% Chrome zoom evidence

- Browser: installed Google Chrome 151.0.7922.77.
- Physical outer window: 3440 by 1328 pixels in both observations.
- At reset 100%: device pixel ratio 1; CSS viewport 3440 by 1151.
- At actual 200%: Chrome's toolbar exposed `Zoom: 200%`; device pixel ratio was 2; CSS viewport
  was 1720 by 575; document horizontal scroll width was 1720.

At 200%, a second exact-implementation-head journey used only keyboard navigation. Focus reached
the demo disclosure, load button, reviewer input, confirmation button, and analysis button after
8, 1, 13, 36, and 9 bounded Tab presses respectively. Each target was enabled, inside the current
viewport, and showed either the three-pixel focus outline or the explicit focus shadow. The full
evidence matrix, `5 · Summary & Export`, all three download controls, and `Review status: Action
required` appeared. No named visible button, link, input, textarea, select, summary, or button-role
element extended beyond the horizontal viewport. Chrome was restored to device pixel ratio 1 and
the 3440-by-1151 CSS viewport after the run.

This is real native-zoom evidence for the exact Chrome/macOS/display configuration above. It is
not a claim about other browsers, displays, platforms, zoom levels, assistive technologies, or
accessibility conformance. Responsive viewport resizing was not used as zoom evidence.

## Python 3.13 evidence

A genuine uv-managed `cpython-3.13.14-macos-aarch64-none` interpreter was installed from uv's
managed Python distribution. On the implementation tree, a fresh wheel was built and installed
with runtime dependencies into an isolated Python 3.13 virtual environment outside the checkout.

The following checks passed:

- `Python 3.13.14` interpreter identity;
- wheel build and clean runtime-dependency installation;
- `pip check` with no broken requirements;
- installed package metadata and `scopeproof_core.__version__` equality at `0.2.3`;
- `scopeproof --version` and `scopeproof-web --version` at `0.2.3`;
- deterministic benchmark: 12 cases, 13 criteria, zero mismatches, zero must-have False Ready
  outcomes, zero false blockers, and zero unexecuted declared categories;
- comparison benchmark: 2 cases and zero mismatches; and
- installed `scopeproof-web` exact loopback health response `ok`.

The local result establishes Python 3.13 package, CLI, deterministic-gate, and health
compatibility on this macOS host. The separate hosted job must pass on the PR before Linux-runner
Python 3.13 evidence is claimed. Neither result is Linux desktop evidence.

## Unsupported evidence rows

| Row | Classification | Exact boundary |
| --- | --- | --- |
| VoiceOver or another real screen reader | Unsupported current evidence | macOS exposed the installed `com.apple.VoiceOver` service, but two bounded attempts to obtain a controllable, observable VoiceOver state timed out. No speech, caption-panel, focus-announcement, or reading-order evidence was available, so no screen-reader result is claimed. |
| Windows desktop | Unavailable environment | No real Windows environment was available for build, installation, launch, or representative workflow completion. |
| Linux desktop | Unavailable environment | No real Linux desktop environment was available. The headless Ubuntu CI job is package/runtime evidence only. |
| Accessibility conformance | Unsupported claim | Keyboard, focus, native-zoom, DOM, and automated evidence cannot by themselves establish WCAG conformance or usability for every user. |

## Verification status

The focused browser regression, repository contracts, complete local suite, and local Python 3.13
package/CLI/health checks passed on the final executable/test verification tree. Hosted CI passed
the Python 3.11, Python 3.13, locked-environment, full verification, packaged-browser, and CodeQL
checks on the same head. The opt-in informational ScopeProof evidence-review job skipped by design.
The audit-only commit that records these results necessarily follows the tested head and does not
change executable or test content.
