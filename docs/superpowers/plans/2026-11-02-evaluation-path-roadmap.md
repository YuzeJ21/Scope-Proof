# Evaluation path and roadmap implementation plan

> **For agentic workers:** Use superpowers:executing-plans, then independent whole-branch review.

**Goal:** Give ScopeProof one accurate evaluation entry and a bounded next-stage direction.
**Architecture:** Current guidance links to immutable evidence; historical plans stay version-bound.
**Tech Stack:** Markdown, existing pytest contracts, Ruff and protected GitHub CI.
**Spec:** docs/superpowers/specs/2026-11-02-evaluation-path-roadmap-design.md

## Global constraints

Public v0.2.4; current source 0.2.5/record9; PR #221 candidate remains original source/record5.
No publication, product mutation, frozen benchmark edits, personal testing or qualifying reviews.
Stage 3 remains dormant; vendor documentation establishes capability claims, not effectiveness.

## Review focus

Check release/source confusion, false novelty, inflated browser counts, implicit publication
authority and an endless new-feature queue. Inspect each in the guide and roadmap against source.

## Task 1: Current evaluation and product decision

Files: docs/evaluation-guide.md and docs/commercialization/product-direction-2026-11-02.md.

- [ ] Write the version map, optional constructed journey, evidence limits and market tradeoffs.
- [ ] Check commands/labels against existing code and automated journeys; verify official sources.

## Task 2: Route current guidance and close stale priorities

Files: README.md, ROADMAP.md, docs/README.md, docs/releases/v0.2.3-status-and-next-stages.md,
docs/releases/v0.2.5-evaluation-candidate.md, docs/commercialization/stage2-readiness-packet.md.

- [ ] Link the new entry, mark completed handoff, distinguish historical candidate and writer facts.
- [ ] Run pytest tests/test_repository_contracts.py, Ruff, diff/link checks; preserve frozen files.
- [ ] Obtain independent review, resolve findings, create PR and integrate only after required CI.

Validation results and final commit/run identities belong in the PR and external verification
packet; this plan is a preparation record, not a claim that its future merge already passed.
