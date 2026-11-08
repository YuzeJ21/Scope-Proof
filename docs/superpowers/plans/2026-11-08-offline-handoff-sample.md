# Offline handoff sample implementation plan

> **For agentic workers:** Execute this bounded slice inline, then obtain fresh independent engineering review.

**Goal:** Let a new evaluator inspect an actual saved-decision report without installing ScopeProof.

**Architecture:** Use the verified installed public v0.2.6 exporter with the existing immutable native active record. Add only an upfront constructed-example disclosure to its HTML; bind raw and presented output separately. Link the downloadable repository artifact from the existing README/evaluation guide, so the live website's guide route needs no new deployment.

**Tech stack:** Python/Pydantic standalone recipe, self-contained exported HTML, pytest contracts, offline Chromium, existing required CI.

## Design and alternatives

The public site explains offline handoff, but an evaluator currently must install and run the product to obtain any report. The selected outcome supplies that missing inspectable artifact. Reuse the actual public-writer active-rich-v9 record; do not rebuild a corpus or fabricate a current state from a historical bundle. A fresh synthetic lifecycle and another video would duplicate existing inputs or still withhold the report. A new package candidate or architecture extraction lacks a consequential new constraint.

The report remains **Action required**, confirmed revision 2, recorded final acceptance No. Its original earlier Ready history, decisions, references, JUnit audit and runtime assertions remain constructed facts, not human or runtime verification. The download is an active review report with recorded audit context, not a complete importable saved record or export of every historical analysis. Source links use a synthetic repository/head and are not live verification links.

## Global constraints and review focus

- Keep AGENTS.md, application/core, gates, schemas, dependencies, frozen R-002 and all historical/native corpus bytes unchanged.
- Require the verified public v0.2.6 wheel/core and read the input through the public Pydantic storage boundary; never relabel current development as a released producer.
- Preserve raw exporter bytes except one clearly recorded disclosure insertion immediately after the body tag. Validate input, recipe, raw output and presented output identities in a strict Pydantic manifest.
- Generate outside the checkout into a new directory, without network or external execution; repeat for byte-identical output.
- Keep simulation and synthetic-link warnings inside the downloadable file so they survive separation from the guide.
- Check offline rendering at desktop/mobile widths, no automatic network requests/executable content, real blockers, next actions and retained audit context. Rendering checks are not accessibility conformance.
- Preserve v0.2.6 downloads and the exact388b7da Pages publication. No release, new Pages deployment, outreach, personal testing, qualifying reviews or Stage 3 claim.

## Task 1 — Produce a trustworthy no-install sample

- [x] Add focused sample/provenance contracts and observe the missing-artifact failure.
- [x] Implement `scripts/build_offline_handoff_sample.py`: strict manifest, exact public writer guards, immutable input, one-disclosure presentation transform, exclusive output directory.
- [x] Generate twice through the installed public v0.2.6 environment; compare results and original input bytes. Store HTML, download ZIP and manifest under `docs/examples/offline-handoff/`.
- [x] Protect hash-bound recipe/artifact line endings on Windows and verify malformed/tampered provenance rejection. Include sample contracts in the existing Windows lane.
- [x] Verify the sample offline in Chromium, including no network, current status, revision/head, blockers/next actions, synthetic warnings and audit events.

## Task 2 — Route evaluators and integrate

- [x] Link the sample before installation from README and evaluation guide, explain the expected result and synthetic assertions, and document regeneration.
- [x] Close PR #275 and authorized Pages publication42494611672 in current guidance, retaining historical source-only observations.
- [ ] Run focused tests, lint/diff checks, independent engineering review and required exact-head CI; fix supported findings.
- [ ] Merge only after checks pass; verify resulting main and anonymous public sample bytes. Do not deploy or publish another package.

## Evidence ledger

- Baseline: clean main388b7dae276253ac015efd852cd510bc3999f9fd; no open PRs; CI42490554348 and CodeQL42490554069 passed. Authorized Pages run42494611672 deployed that exact revision and passed public file/link/render/media verification. Public package remains v0.2.6, source0.2.7.dev0.
- Two independent read-only gap assessments found no committed exported HTML report and selected the no-install first-use artifact. Existing recipient offline capability is already implemented; this is an evaluation-entry gap, not an installation defect for recipients.
- Packaging decision: GitHub raw HTML is served as text/plain. Provide a deterministic ZIP containing only the labelled report, then link that binary download; the reader extracts and opens HTML locally. This changes no report body or product behavior.
- Local evidence: 166 focused/repository/CI contracts passed; Ruff/diff checks passed. Two public-v0.2.6 generations match in all three files. Independent released-export probe agrees on the original 37,078-byte HTML digest. Four offline viewport captures passed with no body overflow, automatic network requests or browser errors; keyboard scrolling of the evidence region passed. Private evidence is retained under `~/.codex/artifacts/scopeproof-offline-evaluation-sample-2026-11-08/`.
