# Accessibility and platform evidence design

**Date:** 2026-08-09
**Branch:** `codex/accessibility-platform-evidence`

## Objective

Close the highest-value locally executable evidence gaps without turning partial engineering
checks into accessibility-conformance or broad platform-support claims. The slice must preserve the
ScopeProof evidence boundary: deterministic candidates are not correctness proof, and engineering
rehearsals do not advance Stage 1.

## Starting evidence gap

The packaged-browser regression already builds and installs the wheel, blocks non-loopback
networking, and completes the constructed demo at desktop and mobile viewports. It does not prove
a keyboard-only journey because it clicks the demo disclosure and moves focus programmatically.
The repository also has no durable Python 3.13 compatibility lane. Historical responsive checks
are not native zoom evidence, and no real screen-reader result is available.

## Approaches considered

### 1. Selected: durable keyboard and Python 3.13 proof plus bounded native-zoom observation

- Drive the installed-wheel demo with Tab, Shift+Tab where needed, typing, Enter, and Space only.
- Require every primary target to receive an observable focus ring or focus shadow while it is in
  the viewport.
- Keep the existing 1280-by-720 and 390-by-844 contexts, loopback-only networking, and browser
  error assertions.
- Add a separate Python 3.13 CI job that installs dependencies, runs the complete suite and both
  deterministic benchmarks, builds and reinstalls the wheel, checks both CLIs, launches the
  installed workbench on loopback, and requires the exact health response.
- Record native 200% zoom only from a real Chrome session whose toolbar exposes the zoom value and
  whose device-pixel ratio and CSS viewport change consistently. Restore the browser to 100%.
- Attempt VoiceOver only through a real installed service with observable state; otherwise retain
  an unsupported row with the exact missing capability.

This approach creates reproducible regression coverage for the claims that can be automated and
keeps the real-browser zoom observation narrowly described.

### 2. Rejected: emulate zoom with viewport or page transforms

Viewport overrides, CSS `zoom`, device emulation, screenshots, and JavaScript transforms can test
responsive layout but cannot establish native browser zoom. They would preserve the gap while
making the audit wording less trustworthy.

### 3. Rejected: claim platform coverage from hosted runners

A Linux CI runner can establish Python/package/CLI compatibility in that runner. It cannot prove a
Linux desktop workflow, and it provides no Windows desktop evidence. Those rows remain unsupported
until real environments are available.

## Detailed design

### Installed-wheel keyboard regression

The browser helper locates a stable accessible control, advances with page-level Tab presses, and
stops only when that control is the active element. It then asserts:

1. the control is enabled where applicable;
2. its rectangle intersects the current viewport; and
3. computed focus styling has a visible outline or non-none box shadow.

The journey opens `Try ScopeProof`, loads the deliberately constructed demo, enters the asserted
reviewer label, confirms the normalized criteria, and runs deterministic analysis without pointer
input or programmatic focus. It retains the evidence-matrix, fail-closed summary, export-control,
width, browser-error, and loopback-only assertions.

This proves the exact tested primary path and focus treatment. It does not prove every control,
screen-reader announcement quality, WCAG conformance, or usability by a participant.

### Python 3.13 compatibility

Use a genuine CPython 3.13 interpreter. Local evidence covers clean wheel installation, package
imports, both versioned entry points, exact loopback health, and both deterministic benchmarks.
The hosted job adds the complete suite and repeats the installed-wheel checks on Linux. The result
is Python 3.13 engineering compatibility, not Linux desktop support.

### Native 200% zoom

The bounded observation uses installed Google Chrome on macOS. Valid zoom evidence requires all of
the following in the same session:

- the Chrome toolbar reports `Zoom: 200%`;
- device pixel ratio changes from 1 to 2;
- CSS viewport dimensions reduce while the physical outer window remains unchanged;
- the primary constructed workflow completes with keyboard input;
- named interactive controls do not extend beyond the horizontal viewport; and
- the browser is restored to 100% after the check.

The exact host and viewport are recorded. This is not a general claim about other displays,
browsers, platforms, or zoom levels.

### Screen reader and unavailable platforms

VoiceOver counts only if the environment provides both control and observable focus/announcement
evidence. Detecting the application or inspecting the DOM is insufficient. Windows and Linux
desktop rows remain unsupported because those real desktop environments are absent. A headless
Linux CI result must remain separately labelled.

## Documentation and evidence boundary

Create a current accessibility/platform verification audit and update the status roadmap. State
the exact branch head, host, interpreter/browser versions, commands, and failures only after the
corresponding checks run. Preserve the Stage 1 counts at their canonical zero values and do not
infer customer, production, adoption, conformance, or correctness evidence.

## Verification

- Ruff.
- Complete suite with the 95% combined coverage gate.
- Repository contracts.
- Both deterministic benchmarks.
- Reproducible wheel build and clean installation.
- Installed-wheel browser regression.
- Genuine Python 3.13 package, CLI, health, and deterministic-gate checks.
- Final diff, package inventory, branch/remote divergence, and GitHub checks.
