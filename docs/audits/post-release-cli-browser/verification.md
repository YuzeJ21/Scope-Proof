# Post-release truth, CLI parity, and packaged-browser verification

> **Historical evidence boundary:** This audit remains bound to its named commit, tree, version,
> and environment. The [current status](../../releases/v0.2.3-status-and-next-stages.md) supersedes
> unqualified present-state inferences and does not rewrite the results below.

## Evidence boundary

- Date: 2026-08-08 (America/Toronto).
- Branch: `codex/post-release-truth-cli-parity`.
- Checked-out HEAD: `e4b9ea358ddc191dab0e7b9dce5f3de6efad75d3` with tree
  `ab2105f0e7542f7cb06789ad31bf8d8d808ae4e3`.
- The tested product is the uncommitted working-tree change set over that HEAD. The HEAD/tree
  identify the base, not a commit containing the changes in this audit.
- Published release truth checked at startup: `origin/main` and peeled `v0.2.3` both resolved to
  `448c42758ea139bf9203cbf1bb04b02b02ae412c`; Release v0.2.3 was public with wheel, source
  distribution, and checksum assets. Current-main CI `30854382641`, CodeQL `30854382413`, and
  Pages `30854382659` were successful.

This record is local engineering evidence for ScopeProof itself. It does not verify target-PR
runtime behavior, authenticate reviewer authority, prove correctness, establish customer use, or
advance Stage 1. The canonical Stage 1 gates remain 0/5 qualifying reviews, 0/3 practitioners,
0/3 repositories, 0/3 independently observed under-ten-minute completions, and 0/2 reuse-intent
signals.

## Implemented scope

- Active release, roadmap, README, and public-site copy now identify published v0.2.3 and its
  exact release/main evidence instead of treating the release as pending.
- The CLI now exposes validated `resolve`, `verify-runtime`, `final-acceptance`, and `compare`
  commands over the existing core lifecycle and local JSON store.
- The low-evidence acceptance-note rule is shared by CLI and Streamlit.
- Playwright is a development-only extra. The durable browser test builds and installs the wheel,
  launches the installed `scopeproof-web` from an isolated home, and exercises the constructed
  demo without GitHub networking.
- CI retains the protected `verify` job name and runs its explicit browser marker after the
  installed-wheel smoke.

## Source and deterministic gates

| Command | Current-run result |
| --- | --- |
| `uv sync --extra dev --extra research --locked` | Passed; Playwright 1.62.0 was installed from `uv.lock`. |
| `uv run ruff check .` | Passed. |
| Final combined core/UI coverage gate | Passed after PR review repairs: 1,954 tests, 2 intentional skips, 95.06% coverage in 563.45 seconds. |
| `uv run pytest -q tests/test_repository_contracts.py` | Passed: 77 tests. |
| `uv run scopeproof benchmark` | Passed: 12 cases, 13 criteria, 0 mismatches, 0 must-have False Ready outcomes, 0 false blockers, 0 unexecuted categories. |
| `uv run scopeproof comparison-benchmark` | Passed: 2 cases, 0 mismatches; aggregate 3 added, 1 modified, 1 relocated, 3 removed, 1 unchanged. |
| `git diff --check` | Passed with no output. |

The two skipped rows are the opt-in live-GitHub test and the packaged-browser test during the
ordinary suite. The browser test executes only when `-m browser` is explicitly selected, which
prevents compatibility jobs from attempting an uninstalled browser.

## Installed CLI lifecycle smoke

A fresh local wheel was installed with dependencies into a new Python 3.12 virtual environment
outside the checkout. `pip check` passed; `scopeproof --version` and `scopeproof-web --version`
both returned `0.2.3`. The installed deterministic and comparison benchmarks each returned zero
mismatches.

The no-network constructed fixture path then:

1. validated a hash-bound requirements confirmation;
2. created two independently saved reviews;
3. recorded an ordinary AC-01 resolution;
4. atomically recorded four constructed E3 records and their linked manual-verification events;
5. appended final acceptance only after the deterministic prerequisites were met, producing
   `ready`;
6. exported the validated state with four runtime records and six resolution events; and
7. compared the unresolved and completed reviews into a validated three-row comparison.

The runtime values in this smoke are explicitly synthetic command-path inputs. They are not
target-repository observations and must not be reused as product, customer, or Stage 1 evidence.
The installed workbench health endpoint returned exact `ok`; after process-group termination the
endpoint was unreachable and no launched process remained.

A separate minimum-version probe installed the final wheel with Streamlit 1.52.0 into a fresh
Python 3.12 environment. `pip check`, `scopeproof-web --version`, loopback health, and the complete
constructed demo-to-analysis AppTest path passed. The rendered three download controls each had a
deferred file ID and no precomputed URL. This establishes the declared deferred-download floor; it
does not substitute for the current-driver Chromium regression below.

## Packaged Chromium regression

- Host environment: macOS 26.5.1 build 25F80, Apple silicon, Python 3.12.0.
- Driver: Playwright 1.62.0 with Chrome for Testing 151.0.7922.34.
- Command: `uv run pytest -q -m browser tests/browser`.
- Latest result after PR review repairs: passed, 1 test in 24.57 seconds with the final
  loopback-only network guard.

For fresh browser contexts at 1280×720 and 390×844, the test used keyboard activation for the
stable demo-load, criteria-confirmation, and deterministic-analysis buttons. It required visible
criterion evidence, missing-evidence guidance, the fail-closed `Action required` summary, and
enabled Markdown, JSON, and CSV download controls. HTML and body widths stayed within each
viewport. A route guard blocked every non-loopback HTTP request and recorded non-loopback
WebSocket attempts; the final list was empty, so the constructed flow made no observed external
request. No browser-console error or unhandled page error was captured. The installed server used
a temporary `HOME`, and the process group was stopped even on failure.

Native 200% browser zoom was not exercised; viewport resizing is not claimed as zoom evidence.
Screen-reader operation, Windows, Linux desktop behavior, and Python 3.13 remain unverified.
GitHub-hosted evidence is reported separately on PR #185 and does not substitute for this local
installed-wheel browser result.

## Distribution evidence

A fresh build produced:

| Artifact | Entries | SHA-256 | Forbidden inventory matches |
| --- | ---: | --- | ---: |
| `scopeproof-0.2.3-py3-none-any.whl` | 101 | `e3f8f97c6debda647f6c14792aaf56a7708e828670a342dbe5d2a2573f144d8a` | 0 |
| `scopeproof-0.2.3.tar.gz` | 546 | Not recorded because this audit is included in the sdist, making its content hash self-referential. | 0 |

The scan rejected Git state, `.scopeproof`, coverage files, virtual environments, common secret
paths, and caches. Wheel metadata contains Playwright only under the `dev` extra; it is absent
from runtime requirements. The isolated pip install resolved Streamlit 1.61.1, which is within the
declared runtime range; the locked contributor environment remains separately governed by
`uv.lock`.

The final wheel was reinstalled after the independent-review fixes. `pip check`, both version
commands, both installed benchmarks, validated lifecycle-mutation JSON, two-review comparison,
four-record runtime linkage, final `ready` acceptance, JSON export, workbench health, and bounded
process-group teardown all passed.

The pre-PR wheel at commit `1ec899a7d3b9b792db4cd50fef2f0a966d3bd05a` had SHA-256
`b7817801ee196fff6c0eb4a7126819bc5d6d6fbb7ca1ad1cc50854eefe632b70`. That hash is retained as
historical engineering evidence only; it was superseded when the PR review repair changed packaged
CLI and storage code. The intermediate repair wheel had SHA-256
`7f5e989a8237d95c04e55a0b8d3195621b957215e18c68b32c17736314073960`; it was superseded when
the follow-up repair changed packaged workbench and storage code. Later repaired wheels had
SHA-256 `80f06e6868f329f37093b5938375e8d60bc235a147e9e2bf721b3543af9fd329`,
`3cff11a506c7346b80d92a693fd7b71d0404fd1e7390e64268655fed79542f89`, and
`23ac78c8fe7f5d25e1ca1392a8b63e13c18af37cd469698284200e5815d9afe1`, and
`6a45e5da1a2be1630c84265f7c0fa161386f3d9c298657029354038bddcf999b`,
`fe95105bf15528d605c217e4e807332ec473b39fd0a32c970eaec151cd693da9`,
`d58b197a655bb068958fb7711d2a880eaba31c9718dd4a56afd65dd17ea8efd6`,
`4f661c3e3ba5344ceada76d4917cfa975002392e031e1148cc105aee8fac6326`,
`3e4fecee45a0136a65a7ee08c00495c60024f3e2ea41f78d465d603eccbf3106`,
`05c7de221e407c1c2d887f78b280ee5378f2c7d785395e337055f82db3886d83`,
`452a83f5336b5e7b05cf06bdf8e8d3210c1b7d8cc8988ab69e1f40504bb46c74`,
`a95eb10677565e327cbaae69ed60faa47bbd914983c22d4aaccd6ac1c00342fd`,
`39f92637b8bcc4dabe799fa956aab9b9dc27bc2a9b7b0176ff4e99f8c220bcdc`, and
`df3931bf7d9c36c8284f910f4eb2c7e7ba9f32977a07b99d19e4840ef5921c8b`; they were superseded by
the deletion-serialization/portable-lock repair, the CodeQL path-hardening repair, the workbench
read-refresh repair, the criterion-definition comparison guard, and the final click-time export
revalidation repair, the hosted-Ruff union-order repair, and the minimum Streamlit floor repair,
the browser export/lifecycle serialization repair, the CLI export/lifecycle serialization repair,
the CLI comparison snapshot-serialization repair, the unavailable-storage/release-baseline truth
repair, the locked workbench refresh repair, and the locked Summary status snapshot repair,
respectively. The current wheel hash above was reproduced in two fresh
builds, and an equivalent current-tree wheel was installed by the latest packaged-browser run.

## Attempt boundaries

- An initial local browser launch used a Chromium build from the pre-sync Playwright package.
  After the locked environment installed Playwright 1.62.0, Chromium was reinstalled from that
  exact driver and the browser regression passed. CI installs Chromium after dependencies, so its
  ordering matches the successful path.
- The first installed lifecycle smoke mistakenly supplied mutually exclusive `--pr` and
  `--fixture` inputs. That shell block did not fail fast, so none of its lifecycle output is used
  above. The clean rerun used `set -e`, `--fixture` only, and produced the recorded results.
- The first installed health teardown checked the endpoint immediately after termination and saw
  a brief draining response. The verified rerun polled for bounded shutdown and confirmed the
  endpoint became unreachable with no process remaining.

## Worktree hygiene

Every registered worktree was inventoried for exact path, status, merge ancestry, and live remote
branch presence. Seven project-local worktrees were clean, fully merged into `main`, had no remote
branch, and contained no nested repository; they were removed normally and their local branches
were deleted with non-force `git branch -d`:

- `exact-head-post-merge-alignment`
- `exact-head-runtime-evidence`
- `scopeproof-v0-2-1-release`
- `v022-rc-audit`
- `v023-post-merge-alignment-20260731`
- `v023-readiness-sync`
- `workbench-ux-simplification`

The root, `evidence-integrity-hotfix`, R-002, and re-review worktrees remain registered. The R-002
worktree retains its untracked `.coverage 2`; the re-review worktree retains its untracked
`comparison 2.py`; neither was modified. The root `.coverage 2` also remains untracked and was
excluded from all product changes and package inventories. Removed worktree directories contained
no uncommitted files; their commits are already reachable from `main`, although the deleted local
branch names would need to be recreated if wanted.

## Remaining gates and next action

An independent complete-diff review initially reported five Important findings: malformed record
envelopes could escape as tracebacks, mutation metadata lacked a Pydantic contract, Playwright was
range-resolved rather than exact-pinned in pip CI, browser networking was not explicitly blocked,
and the sdist hash claim was self-referential. All five were fixed and independently re-reviewed.
The reviewer then reported no remaining Critical or Important findings. After PR #185 opened, its
automated review found two additional P2 defects: lifecycle CLI read-modify-write operations could
lose concurrent append-only events, and `compare` accepted reviews from different repositories or
pull requests. Both were reproduced before repair. Lifecycle commands now use a store-owned
per-record serialized mutation boundary, and comparisons reject mismatched repository/PR identity
before rendering or creating output. A follow-up review then found that a stale open workbench
could still replace a newer CLI lifecycle event through an unconditional save. That race was also
reproduced before repair. Workbench saves now present their last persisted state fingerprint under
the same per-record lock; a mismatch preserves the newer record, retains the open work as unsaved,
and instructs the user to reopen instead of overwriting. The new store and real-workbench
regressions passed in the final full suite and the latest package/browser proof above. The next
automated review found two further P2 defects: deletion did not participate in record
serialization, and unconditional saves had no Windows-compatible lock fallback. Both were
reproduced before repair. Deletion now shares the per-record lock with lifecycle mutation, and
saves use the standard-library Windows file lock when POSIX `fcntl` is unavailable. Both new
regressions passed in the final full suite and package/browser proof above. CodeQL then reported
one high-severity path-expression alert because the validated review ID was embedded directly in
the lock filename. The alert was reproduced from the check annotation. The final lock filename is
derived from a fixed-length SHA-256 digest instead of review-ID text, with a regression proving
the user-supplied identifier is absent. The final full suite and package/browser proof above cover
that repair; hosted CodeQL is reported separately on PR #185.
The next automated review found one P1 truth defect: a clean open workbench could keep rendering
and exporting cached Ready after an external final-acceptance revocation because it only checked
the cached session fingerprint. That behavior was reproduced before repair. A clean open review
now revalidates and refreshes from the Pydantic-validated persisted record before rendering or
exporting. Pending input is preserved rather than overwritten; concurrent persisted changes or
read failures switch the visible status to `Refresh required` and disable all downloads until the
review is reopened or the draft is cleared. The real-workbench regressions cover the clean
revocation, pending-input, and read-failure paths.
The following automated review found one further P2 comparison-integrity defect: records for the
same repository and pull request could reuse criterion IDs for different confirmed text or
required evidence levels, leading evidence-only comparison to hide the requirement change. That
behavior was reproduced for both fields before repair. CLI comparison now requires full confirmed
criterion definitions to match by criterion ID before any output is rendered or created; mismatch
failures leave both saved records and the requested output path unchanged.
The next automated review found a second P1 truth defect: a final-acceptance revocation could land
after page render but before a precomputed download was clicked. The installed Streamlit
deferred-download API now executes a no-argument renderer at click time. It reloads the saved
record, validates it through the store, requires the exact expected fingerprint, and only then
renders the requested format. Changed, missing, or unreadable records raise one fixed safe error;
the page retains no precomputed download URL. Unit and real-workbench regressions cover unchanged
and externally revoked click-time states.
The following P1 review found that the declared Streamlit 1.37 floor did not support callable
download data. The floor is now 1.52, the first verified compatible release; an isolated final-wheel
probe completed the constructed demo flow with three deferred file IDs and no precomputed URLs.
The final P2 review found a narrower concurrency interval inside the click-time callable: a
revocation could complete after the saved record was loaded but before report bytes returned.
Deferred export now holds the store's shared per-record lock across validated load, fingerprint
comparison, and rendering. A deterministic two-thread regression proves revocation cannot complete
while that export is in progress; the full suite, minimum-floor probe, and package/browser proof
above include the repair.
The exact-head review then found the same ordering gap in `scopeproof export`: its unlocked
load-and-render path could print an accepted report after a concurrent revocation completed. CLI
export now holds the shared per-record lock across validated load, rendering, and output. A second
two-thread regression proves revocation waits for CLI export completion; the final full suite and
package proofs above include this parity repair.
The next exact-head review found that `scopeproof compare` loaded its two records independently, so
a concurrent lifecycle mutation could create a mixed-time comparison; using the same review ID on
both sides could even report a delta against itself. Comparison now acquires each unique record
lock once in deterministic sorted order, loads both records under that shared snapshot, and holds
the locks through rendering and output. Two red-then-green regressions cover distinct-record and
same-record comparisons. The final full suite, packaged benchmarks, and wheel proof above include
this repair.
The following exact-head review found two further truth defects. First, an accepted review whose
saved-store listing became unreadable or unsafe could skip revalidation and retain cached
`Review complete`. A previously saved open review now clears its cached saved-state trust, marks a
refresh conflict, and disables exports whenever storage availability cannot be established; the
red-then-green AppTest covers that path without exposing the underlying error. Second, the README,
roadmap, and release-status document called the v0.2.3 release commit the current `main` tip, which
would become false immediately after this PR merges. Those files now identify the immutable
release baseline and separately date the 2026-08-08 `origin/main` observation. The final full suite,
repository contracts, packaged browser proof, and wheel proof above include both repairs.
The next exact-head review found that the workbench's persisted refresh still loaded without the
shared record lock, allowing an overlapping lifecycle revocation to complete between the read and
hydration. The refresh now holds the per-record lock across validated load, fingerprint comparison,
pending-input conflict handling, and hydration. A red-then-green AppTest proves the clean-open
refresh uses that shared lock; the related revocation and fail-closed refresh regressions remain
green. The final full suite, repository contracts, browser proof, and wheel proof above include the
repair.
The following exact-head review identified the remaining interval between refresh-lock release and
visible Summary status rendering. The workbench now takes a second validated persisted snapshot and
holds its per-record lock through status, gate-reason, guidance, and provenance rendering. If the
record changed in the interval, the Summary hydrates the newer state or fails closed for pending
input; deferred downloads retain their separate click-time validation lock. The focused regression
requires both refresh and status rendering to participate in the shared lock. The final full suite,
repository contracts, browser proof, and wheel proof above include the repair.
The latest exact-head review found that the low-evidence acceptance-note rule still lived only in
the CLI and Streamlit adapters. A different core caller, or a forged saved state, could therefore
record an `accepted` decision below the criterion's required evidence level without attributable
rationale and later satisfy the deterministic final-acceptance prerequisites. The shared policy is
now enforced both when the core lifecycle appends a resolution and whenever a bundle or saved
lifecycle state crosses trusted validation. Red-then-green regressions cover both boundaries;
comparison fixtures now carry explicit rationale instead of relying on the prohibited state. The
final full suite, repository contracts, browser proof, two reproducible wheel builds, and clean
installed-wheel benchmarks above include the repair.

Reviewer/source-owner identity is asserted, not authenticated. The GitHub Action remains opt-in
and informational rather than a required branch-protection check. Native zoom, screen reader,
Windows, Linux desktop, Python 3.13, and genuine external Alpha use remain outside current
evidence.

The next safe action is owner review of the current PR after its repair commit and available hosted
checks are complete. Merge, release, issue mutation, and outreach remain separate owner gates.
