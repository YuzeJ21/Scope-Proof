# Covered-suite performance maintenance — 2026-10-29

## Question and baseline

Can ScopeProof reduce the repeated covered-suite delay without reducing verification?
The owner delegated automatic execution and declined personal testing and qualifying reviews.
At branch start, main `979d42318cdcecc84894a084feb6c262dc13ff94` was clean, PR #217 was merged,
all resulting-main checks were green, and no engineering PR or defect report was open.

[Main CI 40932800933](https://github.com/YuzeJ21/Scope-Proof/actions/runs/40932800933)
spent 15m34s in its covered Test step (18:39:35–18:55:09 UTC; pytest reported 932.94s).
The preceding main run also spent about 15 minutes there. PR #212 already removed the
demonstrated cross-job serial wait; further dependency restructuring was not justified.

This slice answers one bounded maintenance question. It adds no product capability or new
benchmark cohort and creates no genuine independent-use evidence.

## Controlled local comparison

The same complete test population ran sequentially at that unchanged source revision, in one
locked macOS environment: Python 3.12.0, pytest 9.1.1, pytest-cov 6.3.0, coverage 7.15.2,
Streamlit 1.66.1 and Pydantic 2.13.4. Captured dependency manifests matched exactly.
Each run passed **2,705 tests with 8 intentional skips**. Covered runs used separate new
`COVERAGE_FILE` paths and were never combined with each other.

| Mode | Whole-command wall time | Coverage |
| --- | ---: | ---: |
| Default CTracer | 623.584s (10m23s) | 95.114852% |
| Bare pytest | 250.011s (4m10s) | Not measured |
| Requested SysMonitor | 263.039s (4m23s) | 95.114852% |

The covered command retained `--cov=scopeproof_core --cov=apps`,
`--cov-report=term-missing:skip-covered`, `--cov-fail-under=95`, and the complete suite.
All three commands added only `--durations=40 --durations-min=0.5` diagnostics. The baseline
had no core override and its collector probe selected `CTracer`; the candidate requested
`COVERAGE_CORE=sysmon`. Private Pydantic-validated observations retain exact commands,
dependency manifests, timestamps and outcomes without publishing local environment paths.

Thirty-nine of the default covered run's forty slowest calls were Streamlit AppTest cases.
The slowest legacy-reopen case took 10.66s covered, 4.03s bare and 4.46s with SysMonitor.
A large safe-text redaction case took 5.95s, 1.77s and 1.86s respectively. This controlled
comparison supports reducing tracing overhead; it does not justify removing UI interactions,
Pydantic validation, gate recomputation or source-identity checks.

The candidate reduced local covered wall time by **57.82%**. This is one sequential comparison,
not a statistical performance guarantee. Hosted runners and unlocked dependency resolutions
differ: baseline hosted CI used pytest 9.2.0 and coverage 7.17.0. Hosted timing must be read
from the actual PR and resulting-main runs, not extrapolated from this local result.

## Coverage accounting

Both covered databases had exactly the same 64 measured files, 12,712 executable statements,
14 excluded lines, 621 missing lines, empty/default context and line-only mode. Per-file
**executable, excluded, executed and missing line sets all matched exactly**. The two separate
database files also had the same SHA-256:
`6b19f489288da116f07e60cff5ced3f55e48155bf2bc5ae6c71916c2c8290155`.
They remain private because coverage data contains local paths. This was not an aggregate-score-only
comparison or a merge of old and new measurement data.

The new [accounting regression](../../tests/test_coverage_accounting.py) uses trusted constructed
code in a disposable directory and real nested pytest-cov collection. It requires:

- Actual `CTracer` or `SysMonitor` collectors in both the inner pytest process and its child.
- Measured main-thread, joined worker-thread, raised/caught-exception and subprocess-only lines.
- One deliberately uncalled line remaining missing, with no exclusions.
- Existing pytest-cov child startup and combine behavior, rather than manual coverage startup
  in the child or hand-combined databases.

The outer launch clears only enclosing measurement/test options that would contaminate the
isolated probe. The inner test's child inherits pytest-cov's actual `COV_CORE_*` environment.
A negative control that removed that child inheritance failed; restoring it passed both core
cases. Python 3.11 explicitly skips only the new unavailable-SysMonitor case and still runs
the CTracer control. Windows runs both new cases explicitly.

## Implementation and limits

Only the Python 3.12 engineering job selects `COVERAGE_CORE=sysmon`. A preflight starts the
configured collector and fails unless its observed name is `SysMonitor`; it was exercised
with an intentional CTracer mismatch (exit 1) and SysMonitor (exit 0). The small guard and
accounting probe intentionally inspect coverage's private collector name. Development tooling
is bounded to `coverage>=7.15.2,<8`; a changed tool interface must fail rather than silently
claim the requested engine was selected. The locked version remains 7.15.2; no dependency
version changed in the lockfile.

Coverage documents this core for Python 3.12+ and its restrictions around branch coverage,
dynamic contexts, plugins and some concurrency libraries. Current CI uses ordinary threads,
line coverage and default contexts. Reassess the engine if those requirements change; do not
drop a coverage requirement to retain speed. See the [version-bound configuration reference](https://coverage.readthedocs.io/en/7.15.2/config.html#run-core),
[process guidance](https://coverage.readthedocs.io/en/7.15.2/subprocess.html), and
[PEP 669's interpreter-wide monitoring model](https://peps.python.org/pep-0669/).

Duration diagnostics are appended to the existing three full-suite commands. All original
assertions and test selection, both coverage targets, the unrounded 95% check, five independent
engineering lanes, fail-closed `verify`, separate CodeQL, compatibility checks and installed-wheel
browser journey remain. Existing Windows checks remain and gain the accounting regression.

## Integration finish line

Full-suite, coverage, packaging/browser, compatibility and review results are bound to the exact
PR head and resulting main in the PR's verification record. Additive accounting tests change
later suite counts; the 2,705-case timing comparison above remains frozen at its named baseline.
Do not rewrite that comparison or historical R-002 expectations to improve a score.

After reviewed passing integration, return to bounded maintenance. Public v0.2.4 assets and
tags, frozen R-002, application source and gate policy are unchanged; source remains unreleased
`0.2.5.dev0`. Stage 1 remains closed at zero and Stage 3 dormant. No personal testing,
qualifying reviews, customer validation, beta completion, accessibility conformance, release,
deployment or outreach is claimed or initiated.
