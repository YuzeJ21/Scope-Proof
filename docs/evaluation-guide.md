# Start here: evaluate ScopeProof

ScopeProof helps a technical reviewer explain and revisit an acceptance decision: which
confirmed requirements have candidate evidence, what remains unresolved, and what changed
since the recorded decision. A PM or requirements owner is the proposed report recipient.
These roles and the value of the workflow have not been independently validated.

This is an optional evaluation guide, not a request for the project owner to test the product
or supply qualifying reviews. All verification cited below is automated engineering evidence.

## Choose the right version

Use the **v0.2.6** wheel when its [GitHub Release entry](https://github.com/YuzeJ21/Scope-Proof/releases/tag/v0.2.6)
contains the final source identity, wheel, source archive, checksum manifest and completed
public-download verification. The [GitHub Releases page](https://github.com/YuzeJ21/Scope-Proof/releases)
is authoritative for availability. Until those are available, use the verified **v0.2.5** fallback.
Follow the [README Quickstart](../README.md#quickstart) for both install paths.

| Path | Identity and capabilities |
| --- | --- |
| **v0.2.6** source / final release build | Adds the decision overview, offline HTML download, acceptance rationale, source-conflict explanations and saved requirements comparison described in [v0.2.6 changes](../CHANGELOG.md#026--evaluation-release-build). Writes v9. Source identity alone does not establish publication; use its wheel only after the release entry and public verification above are available. For source work, use the [locked contributor setup](development-environment.md#create-or-refresh-the-environment). |
| Published **v0.2.5** fallback | [Evaluation release](https://github.com/YuzeJ21/Scope-Proof/releases/tag/v0.2.5) from `72cac01ea6abb99beaf714396eb610fa39fe84f0`. Includes saved comparisons, audited references, JUnit audit history, typed criteria and complete-record handoff. Writes v9. |
| Published **v0.2.4** | [Earlier release](https://github.com/YuzeJ21/Scope-Proof/releases/tag/v0.2.4). Writes v5. |
| Historical private **0.2.6.dev0** candidate, unpublished | The [fixed-source packet](releases/v0.2.6-dev0-evaluation-candidate.md) records this development artifact's identities and constructed checks. It is not the final v0.2.6 build or a public-download verification record. |
| Historical private **0.2.5 candidate**, PR #221 | Prepared at `4f12ae02dee277705d17ac6ab94f0a74f99be346` with its own v5 upgrade evidence. See the [dated guide](releases/v0.2.5-evaluation-candidate.md). |

Keep each candidate's recorded identity intact. A final v0.2.6 package requires its own
versioned build and verification; a renamed development archive is not a final release.

Back up local reviews before switching versions. The default store is `~/.scopeproof/reviews`.
Do not point an older release at newly saved v9 records or assume downgrade compatibility.
Complete saved records can contain requirements, source excerpts and asserted reviewer details;
share them only when those contents are appropriate to share. Recorded identity is not authentication.

## Run the released source

For v0.2.6, first check the completed public verification and final source identity in its
Release entry. Use a new directory, Python 3.11–3.13 and [uv](development-environment.md):

```bash
git clone https://github.com/YuzeJ21/Scope-Proof.git ScopeProof-evaluation
cd ScopeProof-evaluation
git checkout --detach v0.2.6
uv sync --extra dev --extra research --locked
uv run scopeproof --version
uv run scopeproof benchmark
uv run scopeproof-web --host 127.0.0.1 --port 8501
```

Confirm that the checked-out commit matches the source named in the Release entry; the launcher
reports version `0.2.6`. If v0.2.6 is not yet publicly verified, use the v0.2.5 fallback source
instead: replace the checkout command with
`git checkout --detach 72cac01ea6abb99beaf714396eb610fa39fe84f0`. That launcher reports `0.2.5`.
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
   For an installed v0.2.5 or v0.2.6 wheel, run
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

For final v0.2.6 artifacts, use only the completed public verification recorded in its
[GitHub Release entry](https://github.com/YuzeJ21/Scope-Proof/releases/tag/v0.2.6). Source changes,
private candidate checks and earlier-release results do not establish those downloads' identity
or installed behavior.

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
Stage 3 stays dormant. The owner separately authorized final v0.2.6 publication and automatic
public-download verification. This guide does not authorize another release, deployment or
external contact, and requests no personal testing or qualifying reviews.
