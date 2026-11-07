# Evaluation Consolidation Implementation Plan

> **For agentic workers:** Execute this bounded plan inline, then obtain fresh independent engineering review. User authorization delegates routine design and execution; no human review checkpoint is requested.

**Goal:** Close the accumulated engineering milestone with accurate guidance and an unpublished source-bound evaluation candidate.

**Architecture:** Documentation and verification only unless a consequential defect is reproduced. Build from a clean fixed source; preserve native public-writer originals and validate copied records with the installed reader.

**Tech Stack:** Existing Python/uv/Hatch, Pydantic, installed CLI, Playwright and GitHub CI.

**Spec:** [Current priorities and delegated goals](../../../ROADMAP.md#current-priorities--2026-11-07).

## Global Constraints

Follow AGENTS.md. Keep `0.2.6.dev0` unpublished; public v0.2.5 retains its identity.
Preserve frozen R-002, explicit confirmation, deterministic fail-closed gates and original history.
No personal testing, qualifying reviews, release publication, deployment or outreach.

## Review Focus

- A public-version walkthrough must not promise development-only controls.
- A native upgrade must use the real public writer, not a forged version field.
- Producer metadata must remain distinct from current-reader validation.
- Package/browser results must name the artifact actually installed.
- Evidence added after the candidate source must not be claimed part of its artifact.

## Task 1: Consolidate direction and freeze source

- [x] Reconcile README, evaluation guide, changelog and roadmap against `72cac01..95897bc`.
- [x] Preserve dated research and redirect current guidance; close #269.
- [x] Validate links and diff, then commit the candidate's clean source.

## Task 2: Verify the fixed candidate

- [x] Archive the exact source; build wheel/sdist and compare direct/source-built wheel bytes.
- [x] Verify clean wheel/source installs, Python compatibility, deterministic benchmarks,
  installed CLI/browser journeys and native v0.2.5-writer records on copies.
- [x] Record hashes, source, commands/results and limitations in a validated private manifest and
  a reviewable repository packet. If source changes are needed, regenerate affected artifacts.

## Task 3: Review and integrate

- [ ] Obtain fresh independent review of documentation and candidate evidence; resolve supported findings.
- [ ] Merge only after the reviewed exact head passes required CI; verify resulting main and clean checkouts.
- [ ] Report product/architecture gaps and stop at the named evidence gate.
