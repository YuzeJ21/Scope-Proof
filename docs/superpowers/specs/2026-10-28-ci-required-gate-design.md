# Required CI gate and parallel verification

## Demonstrated need

The owner requested the next high-value automatic maintenance task, without personal testing or
qualifying reviews. Main `1950e3b54f39d1da7ddce6ff76193c34e8bbf870` is clean and its CI is green.
Current branch protection requires `verify` and `CodeQL`, with strict base freshness.

The current expensive `verify` job waits for four independent compatibility/locked jobs despite
consuming none of their outputs. In resulting-main run 40581903395 the longest prerequisite took
7m41s, then `verify` took 17m49s. The first job started at 20:52:39 UTC and verification finished
at 21:18:12 UTC: 25m33s overall. Avoiding the dependency can remove serial waiting; hosted capacity
and test-duration variation still determine actual elapsed time.

The default dependent job is also skipped after prerequisite failure. GitHub documents that a
required dependent job skipped this way may not block merging, and recommends `always()` plus
`needs`. This is a documented structural risk, not a demonstrated hosted bypass in ScopeProof.
See [required-check guidance](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks#handling-skipped-but-required-checks).

## Chosen approach

Rename the existing expensive workload to `engineering-validation`, remove only its prerequisite
dependency, and preserve its full steps and order. Keep the four other lanes. Add a final job
whose ID and check name are `verify`, whose job condition is `${{ always() }}`, and whose direct
dependencies are exactly all five engineering lanes.

The aggregate has one mandatory Bash step, no checkout or installation, and a short timeout.
Bind five environment variables directly to the corresponding `needs.<job>.result`. Its actual
shell script must accept only literal `success` from all five. Failure, cancellation, skipped,
blank, missing, whitespace-altered and unexpected results must fail. No `continue-on-error`,
optional step condition, or branch-protection change is allowed.

Leaving the graph unchanged preserves both the serial delay and skipped-gate risk. Simply removing
the current `needs` would weaken the required compatibility gate. Sharding tests or changing
caching/runtime dependencies adds unrelated scope. The aggregate approach preserves all checks.

## Boundaries and tradeoffs

Peak independent engineering jobs rises from four to five, plus a short aggregate afterward.
The expensive workload now also runs when another lane fails; runner contention can offset some
wall-time savings. Record actual start/end times and overlap without promising a fixed speedup.
Product code, deterministic gates, criteria/reviewer decisions, versions, published assets,
frozen R-002, branch protection, workflow triggers/permissions and existing diagnostics stay intact.

Finish after graph/status regressions, lint, independent agent review, exact-head hosted checks,
merge, and resulting-main verification. Remain in Stage 2 maintenance; Stage 3 is dormant.
