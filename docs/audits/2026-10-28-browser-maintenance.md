# Bounded automated browser investigation — 2026-10-28

## Baseline and bounds

The source baseline was main `9301e77b1eec1aa0e14bfdc45fa6a2fd3c8cf70e`.
Local main and live GitHub matched, main CI was green, and no PR was open.
The owner authorized automatic investigation, supported repairs, and merge after checks/review,
without personal testing or qualifying reviews. Stage 3 remains dormant; no release or deployment
is authorized. The published version remains v0.2.3; these changes are unreleased `0.2.4.dev0`.

Up to five unchanged installed-wheel journeys were planned, stopping at the first failure.
Each used disposable storage, loopback-only browser requests, and existing failure diagnostics.
The batch stopped after run four:

| Run | Result | Elapsed |
| --- | --- | --- |
| 1 | passed | 42.93 s |
| 2 | passed | 43.53 s |
| 3 | passed | 42.77 s |
| 4 | failed: deferred JSON download stayed loading after Markdown | 48.32 s |

Command for each run, with a fresh temporary directory:

```text
SCOPEPROOF_BROWSER_DIAGNOSTIC_DIR=<run>/diagnostics uv run --no-sync python -m pytest -q \
  -m browser tests/browser/test_packaged_workbench.py::test_installed_wheel_primary_path_in_chromium \
  --basetemp <run>/pytest
```

The fourth run's trace shows Markdown downloaded, JSON was enabled before its click, no JSON
download arrived within five seconds, and JSON alone remained disabled/loading. The server log
contains no application exception. The diagnostic screenshot, accessibility snapshot, log, and
trace are preserved locally in the `scopeproof-browser-20261028-baseline-4-84xekrqb` temporary
directory. The originally documented missing-dropdown trigger did not recur in these runs.

## Selection-helper defects

A real Streamlit fixture independently renders the server's selected enum and run count.
Typing the complete desired label without clicking its option left the server selection `None`.
The old helper returned immediately because input text matched. The new regression first failed
at the expected server-selection assertion: one failed, one already-selected control passed.

The helper now opens/searches the menu and checks the target option's public `aria-selected`
state. Only an already selected option uses the no-rerun path. Query text must lead to an actual
option click, an observed rerun, and the existing dependent-control checks. No private React state
or clear-button inference is used.

An intermediate repair closed an already selected menu with Escape. The first repaired full
browser run failed: ten checks passed, but the journey's final Reopen action became disabled.
Its trace showed Escape immediately cleared the selected input, then triggered a later server
rerun. The initial server-text assertion had read the previous value before that rerun arrived.
A strengthened preservation assertion failed against that repair (empty input, 3.81 s).
The final helper uses Tab to close this menu and checks both the preserved input and the separate
server-rendered selection. This is a repaired intermediate regression, not a baseline defect.

A separate constructed popup dismissal after `fill()` reproduced the original *failure shape*:
the missing option caused an uncaught `AssertionError`, bypassing the existing retry loop.
That regression failed before replacing the visibility assertion with `Locator.wait_for`.
Its timeout is handled by the existing three-attempt loop. This does not broaden the retry count
or treat a missing option as success. A permanently unavailable query must still fail.

The fixture includes a declared 150 ms server workload so the existing rerun observer can observe
the constructed run. Assertions wait on server-rendered values; there is no sleep-based success
criterion. Already selected choices must preserve the server run count. The fixture is constructed
engineering evidence, not a participant review.

## Deferred-download repair

The installed Streamlit 1.66.1 implementation sends a deferred-download request and, by default,
also triggers a script rerun. Its script-start queue clear does not retain queued backend-operation
responses. A response enqueued immediately before that clear can therefore disappear while the
browser keeps waiting.

A separate real Chromium/Streamlit experiment forced that ordering by deferring a normal
script-start clear until the next response had been enqueued, then invoking Streamlit's unchanged
clear implementation. The JSON callback returned bytes; its response was present before clear,
absent afterward, and never reached the browser. JSON alone stayed loading. This scheduler control
proves the response-loss mechanism; the unchanged run-four trace did not contain the server events
needed to establish that its exact ordering was the same.

| Constructed experiment | Downloads | Script runs | Outcome |
| --- | --- | --- | --- |
| Default, naturally paced | 24/24 | 25 | passed |
| Default, controlled queue ordering | 1/2 | 3 | JSON stayed loading |
| `on_click="ignore"`, same control | 24/24 | 1 | passed |

An earlier unpaced experiment stalled after eleven downloads in both modes, with responses delivered
and both buttons enabled. That different symptom is not evidence of the queue-loss mechanism and
was excluded from the mechanism comparison. It was not diagnosed conclusively.

The app now declares `on_click="ignore"` for the three authoritative review downloads. A new
AppTest regression first failed against the original `ignore_rerun=False` configuration. It now
requires all three buttons to suppress their own reruns while retaining deferred file IDs and
no static export URL. The existing click-time locked-load, fingerprint comparison, Pydantic
validation, pending-input guard, and stale-store rejection are unchanged. The focused new test
and deferred-export regressions passed: four tests.

This uses the public [Streamlit download-button option](https://docs.streamlit.io/develop/api-reference/widgets/st.download_button).
It does not prevent another pending widget from causing a rerun, and does not establish that
every possible framework download race has been eliminated.

## Verification and limits

Completed local checks before the integration commit:

| Check | Command / result |
| --- | --- |
| Browser file | `uv run --no-sync python -m pytest -q -m browser tests/browser/test_packaged_workbench.py --basetemp /tmp/scopeproof-browser-20261028-final-browser` — 11 passed in 77.39 s |
| Deferred export safeguards | New AppTest plus `tests/apps/test_deferred_exports.py` — 4 passed in 1.31 s |
| Lint | `uv run --no-sync python -m ruff check .` — passed |
| Patch whitespace | `git diff --check` — passed |
| Deterministic gate benchmark | `uv run --no-sync python -m scopeproof_core.evals.runner` — 12 cases, no mismatches, zero must-have or uncited-file False Ready |
| Deterministic comparison | `uv run --no-sync scopeproof comparison-benchmark` — 2 cases, no mismatches |

The eleven browser checks comprise one full installed-wheel Chromium journey, four constructed
Streamlit selection checks, and six helper/capture checks. They are not eleven end-to-end journeys.
The installed-wheel journey builds and installs into a fresh environment and uses disposable
review storage. Independent agent review found no actionable issues, including on the final
Tab/preserved-input correction. It did not independently run the suite or establish causation.

The separate local full coverage command is:

```text
COVERAGE_FILE=<temporary>/.coverage uv run --no-sync python -m pytest \
  --cov=scopeproof_core --cov=apps --cov-report=term-missing:skip-covered \
  --cov-fail-under=95 -q --basetemp <temporary>/pytest
```

That run began before the final test-helper-only Tab correction; the full browser file above
ran after the correction. Local aggregate coverage is not represented as exact-commit CI evidence.
The PR's exact-head hosted CI is the integration authority for the final full suite, unrounded
95% coverage floor, Python 3.11/3.13, Windows, locked environment, package installation, browser,
lint, and benchmark checks. Required `verify` and CodeQL must pass before merge; resulting main
must then be verified. No unrelated test failure may be silently retried into a success claim.

The original missing-dropdown trigger remains unexplained. The constructed dismissal regression
verifies bounded recovery from that state, not its original cause. No gate, criteria, reviewer
decision, core rule, frozen R-002 input/result, or external-evidence count changed. Automated actors
and fixtures remain labeled as constructed; none supplies genuine independent-use evidence.
