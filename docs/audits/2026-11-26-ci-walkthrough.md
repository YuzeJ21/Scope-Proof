# Maintained two-build CI walkthrough

## Review finding and completed scope

The private `0.2.9.dev0` evaluation candidate at source `f8be510` already contained
the two-build no-install workflow and extensive engineering verification. It was
outside this checkout. Rebuilding that candidate would duplicate completed work.
The concrete remaining gap was a discoverable, maintained evaluation path in the
repository with next reviewer actions and permanent evidence-attribution checks.

The new example reuses the original three HTML snapshots, producer record, three
CI manifests, three raw fixture runs and two saved reviews. It adds an offline
index, one upfront simulation disclosure to each presented snapshot, inspectable
JSON links, reproducible ZIP packaging, and strict Pydantic presentation provenance.
The original candidate, core engine, evidence/gate rules, public package, older
v0.2.6 example and frozen R-002 research are unchanged.

## Identity and evidence boundaries

Original source: `f8be51021bb95c596802426ef05c15fabf393975`.
Original wheel SHA-256:
`62eb1fdcb25c2b63d74acd26cdba06c8556537c0cda5d78022cfc1a3a86ad1ef`.
Original core identity:
`38297453e9cef186ed8b00cbeddf84b355a7e80888dafee1763e3273d12793df`.

The original wheel digest was freshly verified and all 108 core/UI Python files
were compared with their exact Git-source bytes. All 12 frozen source artifacts
match the private candidate. Their original provenance remains separately available;
the presentation recipe and output files have separate hashes. This is byte identity,
not signed execution, authenticated CI, customer use or runtime acceptance.

The effective state after targeted B is failed/failed/passed. Only row access ran
in that targeted job; the category failure and header pass retain initial B's run
citations. Each presented result identifies its supplying run. All three moments
retain blocked / Action required and final acceptance No. The same B review bytes
and commit are used before and after the targeted run.

## Verification and review

- Baseline: 53 focused source checks passed before implementation.
- The original new-test import failed before the recipe existed. The packaging
  checks then passed, including byte recovery, repeatable outputs, unchanged inputs,
  changed-artifact rejection and refusal of false human/runtime credit.
- Independent engineering review identified two material presentation issues:
  targeted-run attribution and Windows checkout newline conversion. Regressions
  reproduced both failures before their fixes. Result attribution is explicit, and
  `.gitattributes` preserves both frozen artifact trees and the hash-bound recipe.
- Download links are revision-relative so the new example is usable from its review
  branch. Original v0.2.6 links and assets remain intact.
- The final focused run passed 212 tests with one intentional browser skip; full
  repository Ruff and whitespace checks passed. The two reproduced review findings
  passed their regressions after correction. A local broad source run was interrupted;
  full-suite results must come from the branch's exact-head CI, not that partial run.
- Local Chromium launch failed before opening a page because the macOS sandbox
  denied its bootstrap registration. This is unavailable local rendering evidence,
  not a successful browser check. The new offline browser case is included in the
  existing GitHub CI browser invocation and must pass there before merging.
- The Windows compatibility job also runs the source packaging contracts. Fresh
  full-suite, compatibility and browser results belong to the PR's exact head;
  historical candidate checks are not credited to this presentation revision.

This closes one evaluation-readiness milestone. Independent usefulness, time saved,
repeat use and willingness to pay remain unmeasured. Stage 3 remains dormant. No
package release, Pages deployment, outreach or further feature queue follows.
