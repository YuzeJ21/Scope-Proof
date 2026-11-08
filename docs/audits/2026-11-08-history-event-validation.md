# Saved-history operating-envelope assessment

ScopeProof's development reader repeatedly scanned all decision events for every retained
analysis. This assessment reproduced that constraint on valid constructed records below
the existing 64 MiB cap and selected one local algorithm improvement. It establishes no
customer workload, UI latency promise, independent use or Stage 3 readiness.

## Inputs and method

Baseline: clean main `c7499173582e6eaeca00f9421b3ba2f47b155afe` after PR #276;
public package v0.2.6, unpublished source 0.2.7.dev0. New constructed records use the
existing demo analysis, fixed synthetic heads, explicit constructed provenance/actors,
repeated `change_required` events on AC-03 and distinct ordered revisions. Every record
passes Pydantic, deterministic gate, evidence and event-history validation. All are
**Blocked**, with recorded final acceptance **false**. These are not R-002 cases, native
released-writer fixtures, human decisions or executed target-repository observations.

Seven cases contain 1/10/100/500 retained analyses at four events per revision, plus
100/500 at 32 and 500 at 128. There is one additional active revision. A separate
two-event baseline record is 49,479 bytes, SHA-256
`d5ebc8baf71c7c28ac448b8d9ea846dd6eb34b32c4f812c49844dfebaffb1253`.
The largest case is 45,422,705 bytes, 500 histories and 64,128 events, SHA-256
`e505508251bdda958dc395120e22d128d2d090fae8e11f431f3eec43d21c1d81`.
Input bytes and complete state projections remain unchanged after measurement.

Each case/operation uses a fresh isolated Python worker with two sequential observations;
the table reports their median. This is macOS arm64/Python 3.12.0 local API evidence,
with a potentially warm OS cache, not independent cold-start trials or browser timings.
The same immutable files are used before and after. Setup is excluded from operation
timing; a 45-second worker limit includes imports, setup, both observations and final
checks. All 28 workers in each matrix completed without timeout. No target code runs.
Private strict Pydantic records retain per-observation wall/CPU times, source hashes,
input identities, process RSS and preservation checks; original measurements are retained
separately rather than rewritten.

## Measured constraint and change

On the largest case, one instrumented baseline validation passed 64,256,256 event elements
to the unchanged resolution/final-acceptance helpers. They consumed 3.349 of 4.217 seconds.
A controlled ordered-partition replay retained all other validation, passed 128,256 elements
and produced identical complete state JSON in 0.690 seconds. This single fixed-order probe
supports the causal explanation; it is not a general speedup estimate.

The production change groups events **after** Pydantic reconstruction, once per validation
call. Existing helpers receive the ordered list for their explicit revision. Gate, evidence,
unknown-history and temporal checks still run; unmatched events remain in the state for
rejection. There is no persistent cache, skipped validation, schema/cap change or event mutation.
Projection work is proportional to events rather than histories multiplied by events;
other validation/serialization costs remain. The actual implementation also passes 128,256
elements and preserves the baseline complete-state SHA-256
`d0fdb29e18ef6a71ac63a30259d4c7b4c5cf5ce59004fdadc48598752bcf91d2`.

| Largest constructed case, seconds | Baseline | Actual changed reader |
| --- | ---: | ---: |
| Reopen saved record | 4.155 | 1.650 |
| Build history catalog | 7.205 | 1.677 |
| Prepare saved comparison | 12.191 | 3.924 |
| Locked comparison recheck | 8.278 | 2.851 |

The 500-history/16,032-event comparison preparation measured 2.802 → 1.765 seconds.
Small sparse cases do not show a consistent improvement: the 100-history/404-event
comparison measured 0.150 → 0.162 seconds. Timing variation and growing serialized input
prevent a general latency claim. Peak process RSS for the largest workers ranged roughly
525–721 MiB before and 481–629 MiB after; it includes imports, input hashing, setup and
earlier calls, so it does not isolate operation allocation or establish a memory improvement.
The file cap is an I/O safety limit, not a memory or responsiveness guarantee. No safe
maximum history count or product SLA has been established.

## Verification and stopping boundary

`tests/gates/test_history_event_validation.py` uses a small real interleaved state to
bound helper input at twice the retained event count without timing assertions. It checks
empty revisions, differing latest decisions, final acceptance/revocation, unknown history,
unmatched events, unchanged JSON and fresh validation after mutation. Existing gate tests
retain premature-acceptance, runtime-evidence and bundleless-event rejection. The focused
gate/schema/lifecycle/storage/released-record run passed 385 tests. The new checks also run
in the existing Windows lane; complete suites and installed journeys remain required CI gates.

Full input bytes and complete state are compared for all eight constructed inputs. Frozen
research, actual released-writer corpus and public downloads remain unchanged. Exact-head
CI and independent engineering review are required before integration; the PR and resulting-main
run are the authoritative integration evidence, separate from these local measurements.

This closes the reproduced repeated-event-scan constraint. It does not select another
architecture rewrite, cache, release or deployment. Continue only for a consequential
reproduced defect/constraint or a separately chosen product direction. Usefulness and reuse
still require genuine independent evidence and separate authorization; no personal testing
or qualifying reviews are requested.
