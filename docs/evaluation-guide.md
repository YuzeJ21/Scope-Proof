# Start here: evaluate ScopeProof

ScopeProof helps a technical reviewer explain and revisit an acceptance decision: which
confirmed requirements have candidate evidence, what remains unresolved, and what changed
since the recorded decision. A PM or requirements owner is the proposed report recipient.
These roles and the value of the workflow have not been independently validated.

## Inspect a report without installing

[Download the constructed report ZIP](https://github.com/YuzeJ21/Scope-Proof/raw/refs/heads/main/docs/examples/offline-handoff/constructed-v026-review.zip),
extract it, then open its `.html` file in a browser. No ScopeProof installation, server or network
connection is needed to read the downloaded report. The current website's evaluation-guide link
leads here; adding this repository download does not require another Pages deployment.

Expect **Action required**, recorded final acceptance **No**, confirmed revision **2**, and blocker
**AC-03**. Inspect the reasons, next action and recorded decision audit. All actors, decisions,
CI metadata and runtime statements are simulated. Repository/head/source links are synthetic and
do not resolve to a genuine reviewed PR. This report is not an importable saved record or an
export of every historical analysis; recorded earlier acceptance is not current authority.

The [sample provenance and regeneration guide](examples/offline-handoff/README.md) identifies the
actual public v0.2.6 exporter, unchanged constructed input and byte-bound presentation disclosure.
The example supplies zero qualifying-review, genuine-use or runtime-verification evidence.

This is an optional evaluation guide, not a request for the project owner to test the product
or supply qualifying reviews. All verification cited below is automated engineering evidence.

## Choose the right version

**v0.2.7 is published and publicly verified**, built from
`e099679ed63309716a7ce4726557ef794bfd5c80` after PR #278. The
[v0.2.7 Release entry](https://github.com/YuzeJ21/Scope-Proof/releases/tag/v0.2.7) records the final
source identity, wheel, source archive, checksum manifest and completed anonymous-download and
fresh-installation checks. Use v0.2.7 as the default evaluation download. Current source/package
reports **0.2.8.dev0**, unpublished; post-release changes do not alter those release bytes.
Published, publicly verified **v0.2.6** remains an earlier fallback from
`68f5c7af9cdaafe97ab72c1a7f6c8784f65a44e1`.
Follow the [README Quickstart](../README.md#quickstart) for both install paths.

| Path | Identity and capabilities |
| --- | --- |
| Published **v0.2.7** — default evaluation download | [Publicly verified release](https://github.com/YuzeJ21/Scope-Proof/releases/tag/v0.2.7) from `e099679ed63309716a7ce4726557ef794bfd5c80`, with wheel, source archive and checksum manifest. Includes native v0.2.6 history compatibility, CSV/HTML revision labels and bounded event-scan repair, plus constructed browser/sample evidence. No new application feature or record format. Writes v9. |
| Current development source **0.2.8.dev0**, unpublished | Separately identifies post-release entry-point documentation and website changes. It is not a new public package or evidence of a new feature. Use the v0.2.7 tag/downloads for the verified release. Writes v9. |
| Published **v0.2.6** fallback | [Publicly verified release](https://github.com/YuzeJ21/Scope-Proof/releases/tag/v0.2.6) from `68f5c7af9cdaafe97ab72c1a7f6c8784f65a44e1`. Includes decision overview, offline HTML, acceptance rationale, source-conflict explanations and saved requirements comparison; see [v0.2.6 changes](../CHANGELOG.md#026--evaluation-release-build). Writes v9. |
| Historical private **0.2.7.dev0** candidate, unpublished | Its source, version and artifact identities remain historical; it is not final v0.2.7 or public-download verification. The no-install example separately retains its actual public v0.2.6 producer and unchanged input. See the [sample guide](examples/offline-handoff/README.md). |
| Published **v0.2.5** earlier release | [Evaluation release](https://github.com/YuzeJ21/Scope-Proof/releases/tag/v0.2.5) from `72cac01ea6abb99beaf714396eb610fa39fe84f0`. Writes v9. |
| Published **v0.2.4** | [Earlier release](https://github.com/YuzeJ21/Scope-Proof/releases/tag/v0.2.4). Writes v5. |
| Historical private **0.2.6.dev0** candidate, unpublished | The [fixed-source packet](releases/v0.2.6-dev0-evaluation-candidate.md) records this development artifact's identities and constructed checks. It is not the final v0.2.6 build or a public-download verification record. |
| Historical private **0.2.5 candidate**, PR #221 | Prepared at `4f12ae02dee277705d17ac6ab94f0a74f99be346` with its own v5 upgrade evidence. See the [dated guide](releases/v0.2.5-evaluation-candidate.md). |

Keep each candidate's recorded identity intact. Final v0.2.7 was rebuilt and verified separately;
its public archives are not renamed development archives.

Back up local reviews before switching versions. The default store is `~/.scopeproof/reviews`.
Do not point an older release at newly saved v9 records or assume downgrade compatibility.
Complete saved records can contain requirements, source excerpts and asserted reviewer details;
share them only when those contents are appropriate to share. Recorded identity is not authentication.

## Run the released source

For v0.2.7, first check the completed public verification and final source identity in its
Release entry. Use a new directory, Python 3.11–3.13 and [uv](development-environment.md):

```bash
git clone https://github.com/YuzeJ21/Scope-Proof.git ScopeProof-evaluation
cd ScopeProof-evaluation
git checkout --detach v0.2.7
uv sync --extra dev --extra research --locked
uv run scopeproof --version
uv run scopeproof benchmark
uv run scopeproof-web --host 127.0.0.1 --port 8501
```

Confirm that the checked-out commit matches the source named in the Release entry; the launcher
reports version `0.2.7`. The private `0.2.7.dev0` candidate remains historical and unpublished.
For the earlier verified v0.2.6 fallback source, replace the checkout command with
`git checkout --detach 68f5c7af9cdaafe97ab72c1a7f6c8784f65a44e1`. That launcher reports `0.2.6`.
Stop either launcher with Ctrl+C.

## One constructed review, then a handoff

1. Choose **Load deliberately constructed demo**. Keep its constructed source label; if an
   actor field is needed, use an explicitly constructed label rather than a real approval claim.
2. Inspect the four criteria and choose **Apply edits and confirm criteria**, then
   **Run deterministic analysis**. Confirmation is explicit even in a demo.
3. Inspect the candidates and missing evidence. Expected findings are Strong candidate for
   CSV export, Weak candidate for active filters, and No candidate for failure handling and
   `research_exported`. **Action required** is the expected outcome. Do not accept missing work
   just to make the status green. Static test candidates do not prove test execution.
4. Inspect a candidate's exact-head reference and download a report. Confirm the local save
   status before leaving. Reopen the saved ID through **Resume a saved review**; the record
   retains its original decisions and history.
5. Choose **Prepare saved review download**, then **Download saved review
   record**. This complete record is different from an analysis-report JSON download.
6. Start a recipient workbench on a different port and with a separate review folder.
   For an installed v0.2.7 or earlier v0.2.6 wheel, run
   `scopeproof-web --port 8502 --storage-dir "./recipient reviews"`. In a source checkout,
   prefix the command with `uv run`.
   Upload the record, choose **Inspect uploaded review**, inspect its
   repository/head/confirmation/history, then explicitly consent and choose
   **Import inspected review**. Finally select its ID and choose **Reopen local review**.
   Import alone must not replace open work. A collision or the currently open ID is rejected;
   do not rename the JSON or erase an existing review to bypass it.

The sender-to-recipient path is already exercised by the installed-browser tests; no new human
participation is required to complete this engineering milestone. For real public PRs, use the
[confirmed-source workflow](../README.md#public-pr-cli-workflow). A constructed rehearsal never
becomes a genuine review by substituting a real person's name.

## What is verified, and what is missing

The [v0.2.7 Release entry](https://github.com/YuzeJ21/Scope-Proof/releases/tag/v0.2.7) records
completed publication from `e099679ed63309716a7ce4726557ef794bfd5c80`, all three final assets,
anonymous download/hash checks and fresh isolated installations from both public archives.
Its [release-source CI](https://github.com/YuzeJ21/Scope-Proof/actions/runs/42547822181) passed
4,888 tests, 38 intentional skips and 95.5192% coverage, with seven installed CLI checks,
34 browser-suite checks and Python 3.11/3.13, Windows and locked-environment lanes.
Separately, the exact final wheel passed eight fresh browser cases across seven journey families.
Public-archive installation checks ran on macOS/Python 3.11; Windows CI is not evidence of fresh
Windows installation from those downloaded bytes. These counts belong to the release source,
not later documentation commits. Earlier package checks and private `0.2.7.dev0` candidate
results are separate historical evidence.

The completed public verification in the
[v0.2.6 GitHub Release entry](https://github.com/YuzeJ21/Scope-Proof/releases/tag/v0.2.6) binds
the public wheel, source archive and checksum manifest to final source
`68f5c7af9cdaafe97ab72c1a7f6c8784f65a44e1`. The release-source main checks passed 4,842 tests
with 95.5067% coverage; installed verification passed seven CLI checks and 32 browser-suite checks.
These are constructed engineering checks, not a count of independent users or full end-to-end
journeys. Current source changes, private candidate checks and earlier-release results do not
establish those published bytes' identity or installed behavior.

The [native v0.2.6 compatibility assessment](audits/2026-11-07-native-v026-compatibility.md)
records the permanent regression outcome completed in PR #272 at main
`069af259ac17b6c555d10b10f36e7211b068aac4`. Its
[resulting-main CI](https://github.com/YuzeJ21/Scope-Proof/actions/runs/42428549217) passed
4,860 tests, 36 intentional skips, 95.5067% coverage, seven installed CLI checks and 32 browser-suite
checks. That corpus protects future development readers; it does not expand compatibility to every
historical environment or establish downgrade support. The completed PR #273
[revision-label correction](audits/2026-11-07-historical-report-revision.md) uses a selected
analysis's recorded revision in CSV/HTML, preserving `unknown`; it does not turn an analysis-only
report into a complete current review. Pending current-state exports remain blocked. Dedicated
historical JSON/Markdown reports and available download controls are unchanged.

PR #273 resulting main `1d1358097dc34c69c68e93dc5d45066ff4506b1e` passed
[main CI attempt 2](https://github.com/YuzeJ21/Scope-Proof/actions/runs/42441483388/attempts/2):
4,872 tests, 36 intentional skips, 95.5067% coverage, seven installed CLI checks and 32 browser-suite
checks. Attempt 1 retained a 10-second browser-observer timeout before Reopen; two fresh local
journeys passed unchanged before the one failed-job retry. That passing retry did not establish
the synchronization mechanism was fixed. The completed PR #274
[observer investigation](audits/2026-11-07-browser-observer-reopen.md) separates three further
natural baseline passes from a controlled signal-loss replay with the real installed app.
The narrowly supported repair changes only the test's ID commit wait, retaining actual validated
reopening and saved-state/history checks. The exact natural Streamlit transition remains unproven.
PR #274 resulting main `37799a04942e2926bf9c73882a9e0f4e1e44698f` passed
[main CI](https://github.com/YuzeJ21/Scope-Proof/actions/runs/42450620236): 4,872 tests,
38 intentional skips, 95.5067% coverage, seven installed CLI checks and 34 browser-suite checks.
PR #275 resulting main `388b7dae276253ac015efd852cd510bc3999f9fd` passed
[CI](https://github.com/YuzeJ21/Scope-Proof/actions/runs/42490554348): 4,872 tests, 38 intentional
skips, 95.5067% coverage, seven installed CLI checks and 34 browser-suite checks. The separately
authorized [Pages run](https://github.com/YuzeJ21/Scope-Proof/actions/runs/42494611672) then deployed
that exact revision. All 12 public files matched source; 20 link destinations, five viewport sizes,
transcript navigation, video playback and captions passed automatic checks. Form creation routes
require GitHub sign-in; none were submitted. That publication left the v0.2.6 package unchanged.

PR #276 completed the no-install sample; its actual v0.2.6 export provenance remains intact.
PR #277 completed the bounded event-scan repair at resulting main `944c791`; see the
[measurement and limits](audits/2026-11-08-history-event-validation.md). Constructed engineering
evidence establishes no customer workload or responsiveness guarantee. The exact `388b7da`
Pages deployment was separate from final package distribution, which did not deploy it.
The later v0.2.7 entry-point update aligns the current website source and has its own owner-authorized
publication through the [manual Pages workflow](https://github.com/YuzeJ21/Scope-Proof/actions/workflows/pages.yml).
Its run and public verification identify the deployed documentation revision separately from the
immutable package source. The sample and earlier media retain their actual historical producers.

The historical [v0.2.5 public verification record](releases/v0.2.5-public-verification.md) records the downloaded
wheel, source archive and checksum manifest. Both archives passed fresh installation, benchmarks,
and workbench health checks. The downloaded wheel passed the installed CLI checks and a concurrent
sender-to-recipient Chromium handoff. The [release-source CI run](https://github.com/YuzeJ21/Scope-Proof/actions/runs/41900982073)
passed 4,766 tests and 28 browser-suite checks. That browser total includes installed workbench
cases, constructed selection checks, and helper checks.

This verifies engineering behavior on constructed cases. It does not establish time saved,
customer value, independent repeat use, accessibility conformance or a completed beta. The frozen
R-002 candidate result remains 5/20 research criteria, not a production accuracy estimate.
Source can be missed; candidate presence cannot establish correctness. The evaluation-only
[use policy](../USE_POLICY.md), public-only source access and asserted identities limit adoption.

See the [November 2 product assessment](commercialization/product-direction-2026-11-02.md) and
[next-stage roadmap](../ROADMAP.md#current-priorities--2026-11-07). Stage 2 remains active;
Stage 3 stays dormant with external-evidence counts at zero. Final v0.2.7 build, engineering
review, publication and public-download verification are complete. The separately authorized
current-entry alignment includes site publication and automated public verification, not another
package release. No external contact, personal testing or qualifying reviews are requested.
