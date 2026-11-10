# Published v0.2.7 entry points

> Execute this bounded owner-authorized documentation and website update inline, with independent engineering review before merge. No personal testing or qualifying review is required.

**Goal:** Make the README, evaluation guide, roadmap and existing website consistently identify the published, publicly verified v0.2.7 evaluation release.

**Architecture / design:** Update the existing Markdown and static HTML, retaining their layout and supported workflows. The authoritative package source stays `e099679ed63309716a7ce4726557ef794bfd5c80`; the later documentation and Pages revision is separate. Reuse the manual-only Pages workflow after verified integration. Advance only development source identity to `0.2.8.dev0` because the existing immutable-release guard rejects any changed source reusing final `0.2.7`. No application behavior, schema, gate, dependency or published-package change is needed.

**Alternatives:** Rebuilding the package repeats completed distribution work; globally replacing versions would falsify historical records and the actual v0.2.6 sample producer. Only current guidance and its existing contracts should change.

## Constraints and review focus

- Follow AGENTS.md. Do not execute target-repository code or change product behavior.
- Keep the published-version guard intact, including its committed/tracked/untracked comparisons; extend its existing final-version cases to v0.2.7. Correct only current-source headers in companion operating documents. The dynamic editable lock entry needs no version/dependency change.
- Preserve frozen R-002 inputs/results, native released-writer fixtures, release artifacts, historical packets, the constructed v0.2.6 sample and all historical media.
- Bind release claims and test counts to their actual source/run; do not imply the later main or site is the release tag.
- Keep checksum checks, evaluation-only rights, asserted identities, zero external-use counts and dormant Stage 3 explicit.
- Preserve the existing historical fallback installation instructions and manual-only Pages workflow.
- Publication is authorized for this task. Verify the actual dispatched revision, public file bytes, links, release downloads and bounded desktop/mobile/media behavior. Rendering checks are not accessibility conformance or human-use evidence.

## Task 1 — Align current entry points

- [ ] Recheck clean live main, release source/assets, successful main checks and open PRs; capture the current local site.
- [ ] Update existing release/site contract expectations and observe their failure against stale guidance.
- [ ] Update `README.md`, `docs/evaluation-guide.md`, `ROADMAP.md`, `site/index.html` and the current-guide reference in `site/demo-transcript.html`.
- [ ] Run repository contracts, lint, deterministic benchmarks, whitespace checks, and local Chromium previews/link checks. Record bounded results in a dated assessment.

## Task 2 — Review, integrate and publish

- [ ] Obtain fresh independent whole-branch engineering review; resolve supported findings and rerun affected checks.
- [ ] Open a PR and merge only after review and all exact-head checks pass. Verify resulting-main CI separately.
- [ ] Dispatch Pages for the approved resulting main; confirm run/deployment source, then compare all public files with that revision and verify public links/download hashes and rendered layout/media.
- [ ] Confirm clean synchronized checkouts; report the PR, main/deployment identities, checks and remaining limits. No subsequent release, outreach or feature work follows automatically.

The PR, Pages run and private evidence packet record observed integration/publication results separately from this pre-publication plan.
