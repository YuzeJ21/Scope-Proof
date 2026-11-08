# Saved-review ID commit observer investigation — 2026-11-07

Baseline: PR #273 main `1d1358097dc34c69c68e93dc5d45066ff4506b1e`.
Source is unpublished `0.2.7.dev0`; public v0.2.6 is unchanged.

## Observed failure and bounded reproduction

Main CI [42441483388, attempt 1](https://github.com/YuzeJ21/Scope-Proof/actions/runs/42441483388/attempts/1)
passed its full suite, coverage floor, compatibility and installed CLI checks. The browser suite
then reported 31 passes and one timeout in the pending-source continuation journey. After typing
the direct review ID and pressing Tab, the test waited ten seconds for its generic script-state
observer. It had not clicked Reopen or reached a report exporter.

The preserved trace shows an initially disabled Reopen button. About 0.51 seconds after Tab,
the correct ID and enabled button were already visible. The button's enabled state is computed
by the server, and the captured app was connected and not running; the server log had no
exception. The trace did not capture the harness's JavaScript flag, so it does not establish
the exact natural missing/coalesced status-transition mechanism.

Two fresh local repetitions and the unchanged hosted retry passed during PR #273 verification.
This investigation added three bounded natural repetitions against an archived exact baseline;
all passed. These passes mean **not reproduced naturally**, not that the intermittent observer
issue disappeared or that a framework race was proven.

A separately labelled controlled replay used the real installed workbench and saved record.
It suppressed only the test harness's observer signal for the Review ID commit. It did not
mock the application, storage, backend enablement or validated reopen. The old helper timed out
after 11.12 seconds although the server enabled Reopen after about 61 milliseconds. Waiting for
the meaningful control transition at the same ten-second limit, then actually reopening and
checking exported saved state, passed. This reproduces the false-wait failure condition through
controlled signal loss; it is not a claim to have recreated the precise natural Streamlit race.

## Narrow test-only treatment

Only the pending-source continuation journey's direct-ID commit wait is changed. In its fresh
session, require an empty ID and disabled Reopen button before typing. Enter the exact fixture
ID, press Tab and wait for that server-computed button to become enabled. Keep the actual
Reopen click, its existing rerun wait, validated-success notice and no-loaded-source assertion.
The original two-generation history, revision, stored-byte, explicit-confirmation, source-reload,
analysis and downloaded-JSON assertions remain in place.

An enabled button means the ID was committed, not that a saved record was loaded or accepted.
Negative coverage uses a regular empty review directory: a nonempty nonexistent ID can enable
Reopen, but the actual load must show the missing-record error and cannot satisfy success.
The controlled signal-loss variant exercises the full installed continuation/restart journey.

The generic observer is not relaxed globally. There is no timeout increase, arbitrary sleep,
blind action retry, application/core change, schema migration, gate or policy change. This wait
is not generalized to sessions with an old nonempty ID or pending drafts, where enabled alone
would not establish a new commitment. Product guards remain responsible for actual reopening.

## Verification and limits

Preserve the original failure trace, natural-run evidence and controlled-replay provenance
separately. Regression checks must first fail against the old helper, then pass with the narrow
treatment; the missing-record case must still fail the helper's success condition. Required
merge gates include independent agent engineering review, lint, the full suite at the existing
unrounded 95% coverage threshold, deterministic benchmarks, Python/Windows compatibility and
packaged browser checks. Verify resulting main separately. Exact heads, commands, artifacts,
review findings and final counts are retained in the PR and external verification records.

Frozen R-002, immutable native saved histories, prior audits and published assets remain
unchanged. All actors and data are constructed automation, with no target-code execution or
genuine-use/qualifying-review credit. This is test synchronization hardening, not a new product
feature, beta validation or proof against every browser timing failure. Stage 3 remains dormant;
no personal testing, qualifying reviews, release, deployment or outreach is required or performed.
