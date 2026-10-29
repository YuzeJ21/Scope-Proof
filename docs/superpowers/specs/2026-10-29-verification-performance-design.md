# Bounded verification-performance investigation

Baseline: main `979d42318cdcecc84894a084feb6c262dc13ff94`, with PR #217 and all
resulting-main checks green. Public v0.2.4 and unreleased source `0.2.5.dev0` stay unchanged.

## Intent and finish line

Find whether the repeated 15–16-minute covered test step contains avoidable cost. This is a
named maintenance research question, not proof of a defect or a promised speedup. Stop after
one measured repair and reviewed integration, or a documented finding that no safe repair is
justified. The owner delegated execution and declined routine input and participant testing.

## Approaches considered

- **Selected:** compare full bare/covered runs in the same locked local environment, collect
  per-test timing and tracer identity, then profile the primary measured hotspot. Improve only
  proven avoidable work; add timing diagnostics to existing full-suite commands.
- Further CI dependency parallelization is unsupported: PR #212 already removed the demonstrated
  serial wait. Splitting test coverage across workers adds complexity before a cause is known.
- Speculative source-identity caching or fewer UI interactions could weaken mutation detection
  or acceptance-boundary tests. Neither is an acceptable starting optimization.

## Constraints

- Preserve test population and assertions, `scopeproof_core` plus `apps` coverage targets, and
  the unrounded **95%** floor. Diagnostic partial runs never replace the full acceptance run.
- Preserve all five engineering lanes, fail-closed `verify`, strict branch freshness, separate
  CodeQL, installed-package/browser checks and supported-platform verification.
- Record revision, interpreter, dependencies, tracer, commands, outcomes and durations. Local
  timings do not promise hosted speed; record runner and dependency differences explicitly.
- If changing instrumentation, verify it actually activates and compare executable/measured
  source inventories and covered-line data; warnings or lower accounting are not performance wins.
- Preserve deterministic evidence/gate semantics and Pydantic validation. No target-repository
  code executes; constructed automated checks create no genuine independent-use credit.
- Do not change published assets/tags, frozen R-002, stage status or the package version. No
  personal testing, qualifying reviews, publication, deployment, outreach or speculative features.

## Deliverable

A narrow implementation only if measurements justify it, meaningful regressions where behavior
changes, additive timing diagnostics, and a dated evidence record linked from current operating
docs. Independent automated review and passing exact-head checks precede merge; verify main and
return to bounded maintenance. Stage 3 remains dormant.

## Measured implementation decision

The unchanged complete suite took 623.584s with CTracer, 250.011s bare and 263.039s with
SysMonitor in the same locked Python 3.12.0 environment. Both covered runs had identical
per-file executable, excluded, executed and missing lines across all 64 files. This supports
a CI-only engine selection, not changes to the application or its workbench tests.

Select `COVERAGE_CORE=sysmon` only for the Python 3.12 engineering job. Require the observed
collector to be `SysMonitor` before testing; use coverage `>=7.15.2,<8` as the tested tool
boundary. A constructed accounting regression checks both actual cores, ordinary threads,
exceptions, real pytest-cov child auto-coverage and a deliberately missed line. Windows runs
it explicitly; Python 3.11 skips only the new unavailable-sysmon case. Keep all original
suites and gates, and add duration output to their existing full-suite commands.
