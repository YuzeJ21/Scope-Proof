# Evaluation page alignment implementation plan

> **For agentic workers:** Execute this bounded documentation slice inline, then obtain one fresh independent engineering review.

**Goal:** Let an evaluator find the verified download and understand the already-shipped saved-decision workflow from the existing website.

**Architecture:** Correct the static HTML entry and its existing contracts. Retain the established layout and historical constructed media. Pages stays manual-only; source integration does not publish the website.

**Tech stack:** Static HTML/CSS, existing pytest repository contracts, local Chromium previews, GitHub CI.

**Design / approaches:** The inspected page advertises v0.2.4 and unreleased 0.2.5, contradicting public v0.2.6 and source 0.2.7.dev0. Aligning the existing entry is the selected approach. Another package candidate would repeat closed distribution work; a new core feature or refactor lacks a reproduced constraint. No new lifecycle example, generated media, tracking or product functionality is needed.

## Constraints and review focus

- Preserve AGENTS.md, frozen R-002 inputs/results, actual-public-writer fixtures, product source and dependencies.
- Public v0.2.6 and unpublished 0.2.7.dev0 must remain distinct; link the authoritative Release entry and evaluation guide.
- Describe explicit criteria confirmation, candidate evidence, recorded decisions, offline HTML and guarded revisiting accurately.
- Existing video/transcript remain a constructed coverage example, not a current full-lifecycle capture or human-use evidence.
- Keep use rights, asserted identity, zero external counts and dormant Stage 3 visible. No release, deployment, outreach, personal testing or qualifying reviews.
- Check narrow screens, keyboard focus, local assets/anchors, and above-fold desktop actions and evidence boundary. Rendering checks do not establish accessibility conformance.

## Task 1 — Align the existing evaluation entry

- [ ] Capture the current local desktop/mobile page and verify the release identity.
- [ ] Update the existing site contract's obsolete workflow wording and version/guide routing expectations; observe its failure on the stale page.
- [ ] Update `site/index.html` and label the existing media's scope in `site/demo-transcript.html`; preserve assets and layout unless a preview demonstrates a problem.
- [ ] Run existing repository contracts, lint, local link checks and desktop/mobile Chromium previews.

## Task 2 — Close the old milestone and integrate

- [ ] Mark PR #274 complete in README, roadmap, evaluation guide, documentation index and Stage 2 packet; record exact main and CI separately from historical observations.
- [ ] Record a bounded assessment of this source-only website correction, including commands and preview evidence.
- [ ] Obtain independent engineering review, resolve supported findings, and run affected checks.
- [ ] Open a reviewable PR; merge only after all exact-head checks succeed. Verify resulting main separately and synchronize clean checkouts.

## Evidence ledger

- Baseline: clean main `37799a04942e2926bf9c73882a9e0f4e1e44698f`; PR #274 merged; main CI `42450620236`, CodeQL `42450620545`, base advance `42450620222` successful. Public v0.2.6 Release API still identifies `68f5c7af9cdaafe97ab72c1a7f6c8784f65a44e1` and the same three artifact digests.
- Decision: reuse the existing isolated worktree on `codex/evaluation-page-alignment`; no new worktree or participant input is needed.
