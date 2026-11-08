# Saved-review ID commit synchronization plan

**Goal:** Remove a demonstrated false observer dependency from the installed continuation test
without accepting an uncommitted ID or an unvalidated reopen.

**Baseline:** Main `1d1358097dc34c69c68e93dc5d45066ff4506b1e`; see the
[bounded assessment](../../audits/2026-11-07-browser-observer-reopen.md).

1. Preserve the original CI trace and passing retry. Run at most three natural baseline
   repetitions and report their actual outcome without relabelling controlled evidence.
2. Reproduce the observed failure condition in a real installed workbench while suppressing
   only the harness-owned ID commit signal. Keep server/storage/reopen outcomes real.
3. Add a controlled variant of the full existing two-generation journey and a missing-record
   negative. Observe the controlled case fail against the old helper before fixing it.
4. Change only the ID commit wait: empty/disabled precondition, exact typed ID, Tab and
   server-computed enabled outcome at the existing ten-second limit. Keep checkbox and actual
   reopen observers, actual validated-success checks and every persisted-history assertion.
5. Update current roadmap/changelog, closing PR #273 and distinguishing this test-only outcome.
   Preserve application/core, source version, frozen inputs, native records and public releases.
6. Run focused/installed checks, independent agent review and required exact-head CI. Resolve
   supported findings, merge, verify resulting main and synchronize clean checkouts, then stop.

No generic observer relaxation, timeout increase, blind retries, personal testing, qualifying
reviews, new release, deployment or outreach is authorized by this plan.
