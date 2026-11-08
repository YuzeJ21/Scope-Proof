# Evaluation website source alignment

Observed 2026-11-08. This is a static source correction and private rendering assessment.
It is not a website deployment, package release, participant review or customer-validation record.

## Why this slice

Live main was clean at `37799a04942e2926bf9c73882a9e0f4e1e44698f`, after PR #274.
Its [post-merge CI](https://github.com/YuzeJ21/Scope-Proof/actions/runs/42450620236),
CodeQL and base-advance checks succeeded. CI recorded 4,872 tests, 38 intentional skips,
95.5067% unrounded coverage, seven installed CLI checks and 34 browser-suite checks.
There were no open PRs at the checkpoint.

The existing `site/index.html` still described public v0.2.4 and unreleased source 0.2.5.
Its workflow ended at acceptance coverage/export. This contradicted the current evaluation
guide and the shipped saved-decision, offline HTML handoff and revisit workflow. Both independent
read-only gap assessments selected this concrete entry-point problem over another package
candidate, speculative feature or architecture change.

The Release API still identified public v0.2.6 from
`68f5c7af9cdaafe97ab72c1a7f6c8784f65a44e1`, with the same wheel, source and checksum-manifest
digests recorded by its [public verification](https://github.com/YuzeJ21/Scope-Proof/releases/tag/v0.2.6).
This task rechecked metadata; it does not claim another public-download installation exercise.
Development remains unpublished `0.2.7.dev0`, ruleset 2.0.0, saved-record format v9.

## Change and boundaries

- The hero routes readers to the evaluation guide and verified v0.2.6 Release entry, with a
  separate unpublished source identity and an availability link.
- The five existing workflow cards now cover explicit confirmation, exact-head candidates and
  gaps, recorded decisions, offline HTML/complete-record handoff, and guarded revisiting.
- Existing visual/video assets and transcript timings are retained. The image is labelled an
  earlier constructed visual with Stage 1 closed; the recording is explicitly a coverage example
  that does not demonstrate the complete saved-review lifecycle.
- The established CSS, local assets, caption track, transcript, policy links, passive defect
  path and all evidence limitations remain. No form, analytics, remote script or recruitment is added.
- Current documents close PR #274 without rewriting its historical audit, initial timeout,
  natural-run passes or controlled replay evidence. The exact natural Streamlit transition
  remains unproven; no general observer work follows.

Application/core source, gates, schemas, storage, dependencies, native released-writer records
and frozen R-002 inputs/results are unchanged. There is no new product feature or package build.

## Automated preparation checks

The existing truthful/self-contained site contract first failed on the stale workflow and then
passed with current release/source routing and media-scope assertions. The existing release-surface
contract was updated for the evaluation-guide primary action. All 137 repository contracts passed.

Private Chromium previews exercise 1365×768, 1440×900, 768×1024, 390×844 and 320×568, plus the
390-pixel transcript. Checks cover horizontal overflow, local assets/responses, local and
repository-file links, and keyboard skip navigation. Desktop actions and the evidence boundary
are visible at the checked viewport sizes. This is bounded rendering/keyboard evidence, not
accessibility conformance or human usability evidence. Loopback preview servers stop after capture.

Commands:

```bash
python -m pytest -q tests/test_repository_contracts.py
python -m ruff check .
git diff --check
python /path/to/private-artifacts/tools/preview_site.py before
python /path/to/private-artifacts/tools/preview_site.py final
```

Before/after captures, Pydantic-validated preview manifests, recipes and logs live privately under
`~/.codex/artifacts/scopeproof-evaluation-page-2026-11-08/`. The manifests name the source commit,
working-tree status and exact HTML/CSS/workflow file hashes; a dirty-tree capture is not represented
as exact-head hosted verification. The enclosing PR and final integration evidence separately
record independent engineering review, required exact-head CI and resulting-main checks, including
the unchanged 95% coverage floor, frozen benchmarks, installed checks and Python/Windows lanes.

## Stop condition and next gate

Merge this source slice after review and green exact-head checks, then verify resulting main.
`.github/workflows/pages.yml` remains manual-only; no workflow dispatch, tag, package publication,
deployment, outreach, personal testing or qualifying review is part of this task. The deployed
website has not been asserted to change. A future separately authorized Pages publication can
use the corrected source and requires public-page verification of that exact deployed revision.
No new package release is needed for this static-page correction.

Stage 1 remains closed with every external count zero. Stage 2 is owner-led productization.
Stage 3 stays dormant until genuine independent use and separate authorization. Under the owner's
current preference, no personal testing or qualifying reviews are requested. After this correction,
further feature or architecture work needs a demonstrated consequential constraint; another green
CI run alone does not justify expanding the queue.
