# Start here: evaluate ScopeProof

ScopeProof helps a technical reviewer explain and revisit an acceptance decision: which
confirmed requirements have candidate evidence, what remains unresolved, and what changed
since the recorded decision. A PM or requirements owner is the proposed report recipient.
These roles and the value of the workflow have not been independently validated.

This is an optional evaluation guide, not a request for the project owner to test the product
or supply qualifying reviews. All verification cited below is automated engineering evidence.

## Choose the right version

Capability snapshot: PR #250 main `6a74fe9888d54f5edcd3033457c0d9234056024f`.
The version number alone does not identify a development build.

| Path | Available behavior | Important limit |
| --- | --- | --- |
| Published **v0.2.4** | Local workbench/CLI, explicit criteria confirmation, candidate evidence, reviewer decisions and report exports. | Use the [public installation instructions](../README.md#quickstart). It does not contain the later saved-review comparison, selected-reference audit or complete-record transfer workflow. Writer format v5. |
| Current source **0.2.5, unreleased** at the commit above | Adds saved/reopened comparisons, audited selected references, JUnit correction/withdrawal, criteria-change continuation, typed criteria handoff and complete saved-review transfer in CLI/workbench. | Requires source setup; no updated public download is implied. Writer format v9. [Implementation history](releases/v0.2.3-status-and-next-stages.md). |
| Historical private **0.2.5 candidate**, PR #221 | The dependency/upload fixes captured at `4f12ae02dee277705d17ac6ab94f0a74f99be346`. | Not current source despite the same package version. Original bytes and record-v5 upgrade evidence remain fixed. [Historical candidate guide](releases/v0.2.5-evaluation-candidate.md). |

Back up local reviews before switching versions. The default store is `~/.scopeproof/reviews`.
Do not point an older release at newly saved v9 records or assume downgrade compatibility.
Complete saved records can contain requirements, source excerpts and asserted reviewer details;
share them only when those contents are appropriate to share. Recorded identity is not authentication.

## Run the current source deliberately

For the published download, follow the separate Quickstart above. For the exact source snapshot,
use a new directory, Python 3.11–3.13 and [uv](development-environment.md):

```bash
git clone https://github.com/YuzeJ21/Scope-Proof.git ScopeProof-evaluation
cd ScopeProof-evaluation
git checkout --detach 6a74fe9888d54f5edcd3033457c0d9234056024f
uv sync --extra dev --extra research --locked
uv run scopeproof --version
uv run scopeproof benchmark
uv run scopeproof-web --host 127.0.0.1 --port 8501
```

The version should be 0.2.5; the pinned commit supplies the more precise identity. Stop with
Ctrl+C. The local app does not execute target-repository code. This setup is a source evaluation,
not installation of the historical private candidate or a newly published release.

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
5. On current source, choose **Prepare saved review download**, then **Download saved review
   record**. This complete record is different from an analysis-report JSON download.
6. Open a recipient workbench with a review folder that does not contain the ID. If your build
   lists `--storage-dir` in `uv run scopeproof-web --help`, launch it on a different port with
   `uv run scopeproof-web --port 8502 --storage-dir "./recipient reviews"`. For the pinned snapshot above,
   use another machine or OS account. Tabs and browser profiles under the same account share the
   default folder.
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

[PR #250 CI](https://github.com/YuzeJ21/Scope-Proof/actions/runs/41555416496) passed on
`6052d582c11184e2f09265f3e703d1fb7e08704e`; its tree matches the main snapshot above.
[Post-merge CI](https://github.com/YuzeJ21/Scope-Proof/actions/runs/41558970479) also passed.
The PR run recorded 4,760 tests, 95.4841% unrounded coverage, 7 installed CLI checks and
28 browser-suite checks. The browser total comprises **14 installed-workbench cases,
9 constructed selection checks and 5 helper/capture checks**; it is not 28 end-to-end journeys.
Windows/Python compatibility is bounded to the tested lanes, not every desktop or dependency mix.

This verifies engineering behavior on constructed cases. It does not establish time saved,
customer value, independent repeat use, accessibility conformance or a completed beta. The frozen
R-002 candidate result remains 5/20 research criteria, not a production accuracy estimate.
Source can be missed; candidate presence cannot establish correctness. The evaluation-only
[use policy](../USE_POLICY.md), public-only source access and asserted identities limit adoption.

See the [current product decision](commercialization/product-direction-2026-11-02.md) and
[next-stage roadmap](../ROADMAP.md#current-priorities--2026-11-04). Stage 2 remains active;
Stage 3 stays dormant. No release, deployment or external contact is authorized by this guide.
