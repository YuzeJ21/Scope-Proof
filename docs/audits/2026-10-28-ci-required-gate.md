# CI required-gate and feedback-time maintenance — 2026-10-28

## Roadmap review and selected work

The owner asked for the next high-value task that can be completed automatically, without
personal testing or qualifying reviews. The reviewed baseline was clean main
`1950e3b54f39d1da7ddce6ff76193c34e8bbf870`. Live GitHub matched; PR #211 was merged,
its resulting-main checks were green, and no PR was open. The only open issue was the older
voluntary-feedback thread, with no new defect report.

| Remaining gap | Disposition |
| --- | --- |
| Required CI depends on other jobs without an unconditional result check | Address in this bounded slice |
| Expensive verification waits for independent compatibility jobs | Remove the unnecessary dependency and measure scheduling |
| Original missing-dropdown trigger and separate unpaced download anomaly | Preserve unresolved cause limits; do not repeat unchanged journeys without new diagnostics |
| Genuine independent use, repeat use and product demand | Remain unvalidated; no personal testing or qualifying-review program is initiated |
| Broader desktop/accessibility evidence, new adapters, authentication and integrations | No demonstrated need justifies expansion in this slice |

The [roadmap](../../ROADMAP.md) permits demonstrated upkeep and requires stopping after its
completion evidence. Two independent read-only agent audits found no higher-value demonstrated
automatic product gap and supported this CI slice. Their supplied timing interpretation was
checked against live GitHub job timestamps by the root agent.

## Observed baseline

Branch protection requires `verify` and `CodeQL`, with strict base freshness. No protection
setting is changed. In the baseline workflow, `verify` waits for Python 3.11, Python 3.13,
Windows, and the locked environment, but consumes no artifact or output from them.

[Resulting-main run 40581903395](https://github.com/YuzeJ21/Scope-Proof/actions/runs/40581903395)
at the baseline head provides these UTC timestamps:

| Observation | Value |
| --- | --- |
| First compatibility job starts | 2026-10-27 20:52:39 |
| Last compatibility job completes | 2026-10-27 21:00:21 |
| Expensive `verify` starts | 2026-10-27 21:00:23 |
| Expensive `verify` completes | 2026-10-27 21:18:12 |
| Expensive job duration | 17m49s |
| First engineering start to completion | 25m33s |

The serial wait is observable. It is not a promise of a fixed speedup: runner availability,
queue delays and test-duration variation still affect future runs.

GitHub also documents that a required dependent job skipped after prerequisite failure may
not block merging, recommending `always()` with `needs` for required dependent checks.
See [GitHub's required-check guidance](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks#handling-skipped-but-required-checks).
This establishes a configuration risk with the observed protection settings. No actual hosted
merge bypass or deliberately failing participant PR was demonstrated.

## Implementation and safeguards

The old expensive payload is now `engineering-validation`, with no prerequisites. A one-time
comparison against the baseline Git object confirmed its steps are byte-for-byte unchanged.
The three compatibility jobs are unchanged. The locked lane additionally runs the new gate
regressions alongside its existing repository contracts and benchmarks.

The final job ID and check name remain `verify`. It uses `${{ always() }}`, directly needs all
five engineering lanes, and runs one mandatory Bash step without checkout, installation,
optional step conditions or ignored failures. Five environment variables bind directly to their
corresponding `needs.<job>.result`. Every value must be literal `success`.

The aggregate rejects failed, cancelled, skipped, neutral, blank, missing, whitespace-altered
and unexpected results. Its two-minute timeout bounds only this new short job; existing
workload timeout, cancellation, events, permissions, immutable action references, test/coverage
thresholds, packaging order and diagnostic retention remain intact. CodeQL stays separate.

Peak independent engineering jobs rises from four to five, and the expensive payload now runs
even when another lane fails. That can consume more compute on failing runs; this change
optimizes dependency delay and fail-closed aggregation, not total compute cost.

## Local verification

- Baseline repository/workflow contracts: 150 passed in 2.93s.
- Three focused regressions failed against the unchanged workflow: missing independent workload,
  only four aggregate dependencies, and an expensive multi-step job instead of a mandatory
  aggregate. No existing production workload was changed before that red observation.
- New gate module: 17 collected cases. They execute the actual extracted shell script once
  with all-success results, 50 times with per-lane non-success values, and five times with an
  unset result. Expected exit status is the behavior assertion; no shell response is mocked.
- Combined gate/repository/workflow tests: 167 passed in 1.56s.
- `uv run --no-sync python -m ruff check .`: passed.
- `git diff --check`: passed.
- `actionlint -shellcheck='' .github/workflows/ci.yml`: workflow/expression validation passed.
- ShellCheck on the actual new aggregate script: passed.
- Full actionlint/ShellCheck reports two pre-existing SC2034 unused-counter warnings in the
  Python 3.13 and coverage-lane wheel-smoke scripts. The same warnings occur on the baseline;
  those preserved scripts are not rewritten in this slice.
- Deterministic gate benchmark: 12 cases, no mismatches, zero must-have or uncited-file False Ready.
- Deterministic comparison benchmark: two cases, no mismatches.

The structural reader is intentionally bounded to this workflow's block-style layout; actionlint
provides native YAML/expression validation. Status tests prove the actual shell decision for
constructed inputs. They do not reproduce every hosted cancellation ordering or a merge bypass.

## Integration evidence and finish line

The final PR head must pass all six jobs, CodeQL, and independent code review. Full-suite,
unrounded 95% coverage, installed-wheel/browser and compatibility results remain bound to the
actual hosted head. Compare hosted job start/end timestamps to establish overlap; record the
actual duration without attributing all variation to the graph change. The PR's verification
record carries these integration and resulting-main run links after execution.

### First hosted run and test-tool compatibility repair

At initial head `7d143d2153992842bd13c8d421076164c034efe1`,
[run 40617239996](https://github.com/YuzeJ21/Scope-Proof/actions/runs/40617239996) started all
five engineering lanes at 2026-10-28 01:48:41 UTC, demonstrating the intended scheduling overlap.
The unlocked lanes installed pytest 9.2.0, while the locked lane retained 9.1.1. That run failed;
it is not successful performance evidence.

Pytest 9.2's automatic byte-parameter naming called a deliberately throwing byte subclass's
`__len__` during R-002 verifier test collection. The same error was reproduced locally with
an isolated 9.2 overlay. Explicit IDs for the two existing adversarial cases avoid framework
introspection while preserving the exact byte objects, sentinels and verifier assertions.
The complete verifier module then passed under both versions: 104 cases each.

Windows reported two storage-test failures from unconditional process-global `os.fstat` mocks.
All four backend variants failed locally under 9.2. A full traceback confirmed pytest capture's
`FDCapture.snap` called the patched function on its own output file. The two test injections now
replace only the storage module's OS binding with a proxy; product code and real filesystem
operations stay unchanged. Added unrelated-descriptor probes verify global file metadata access
still works while the intended storage faults and ambiguous-file preservation assertions remain.
The full verifier/storage selection passed under 9.2 (276 cases); the expanded locked selection
passed 443 cases. The local older AnyIO plugin emits a pytest deprecation warning under the overlay;
no dependency pin or runtime change was introduced to hide it.

The final `verify` job actually ran after those upstream failures and exited 1 on the failed
Python 3.11 result. Its check was failure, CodeQL was success, and the PR reported `BLOCKED`.
No failing-head merge was attempted. This is observed hosted rejection, beyond the synthetic
script cases, but still not exhaustive evidence for every cancellation ordering.

These repairs change test IDs and fault isolation only. Frozen R-002 inputs, labels, results,
runtime verifier behavior and storage behavior remain unchanged. The failed run is preserved;
the repaired source requires a new exact-head run, not a same-head retry into a green claim.

No product gate, criteria confirmation, reviewer decision, Pydantic review schema, rule/version,
frozen R-002 input/result, external-evidence count, release asset or deployment is changed.
The browser suite remains eleven checks, including one full installed-wheel journey. Stage 3
stays dormant; complete this maintenance slice and stop.
