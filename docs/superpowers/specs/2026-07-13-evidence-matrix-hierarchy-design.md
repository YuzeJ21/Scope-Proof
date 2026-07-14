# Evidence Matrix Hierarchy Design

## Context

The packaged v0.1.15 first-use audit captured a nine-column evidence matrix at a 1280 by 720
desktop viewport. Long concern text forces narrow columns and heavy wrapping, so the overview reads
like a compressed detail report. The current `0.1.16.dev0` line has not changed that structure.

Evidence:

- `/Users/yjian070/.codex/visualizations/2026/07/13/scopeproof-v0.1.15-first-use-audit/04-matrix.png`
- `/Users/yjian070/.codex/visualizations/2026/07/13/scopeproof-v0.1.15-first-use-audit/notes.md`

## Goal

Make the matrix a scannable overview while keeping all existing evidence facts available in the
selected criterion's detail section.

## Options considered

1. Keep all nine columns and add horizontal scrolling. This preserves the current structure but
   does not improve hierarchy or first-use comprehension.
2. Replace the Markdown table with an interactive dataframe. Rejected because the repository has
   already recorded instability in the supported pandas and Arrow AppTest path, and the workflow
   does not need grid interaction.
3. Keep six overview columns and move confidence, candidate count, concern, and human-resolution
   context into Criterion Detail. This reuses the current stable Markdown pattern and aligns deep
   information with the existing inspection surface.

Choose option 3.

## Product behavior

The matrix keeps these columns:

- Criterion
- Requirement
- Priority
- Status
- Evidence
- Human resolution

The selected Criterion Detail adds one compact facts line containing required evidence, observed
evidence, confidence, candidate count, and current human resolution. The existing provisional
reason remains immediately below it, so the removed matrix `Concern` text is not lost.

Remove the unlabelled bold criterion lines rendered below the table because they repeat the
criterion, status, and requirement already present in the matrix and do not navigate or control
the selected detail.

## Boundaries

- Do not change criteria, findings, evidence, confidence calculation, filters, resolutions, gates,
  persistence, exports, schemas, or benchmark labels.
- Do not execute PR code or add a dependency, API, service, billing, telemetry, or external write.
- Keep the core engine independent from Streamlit.
- Keep version `0.1.16.dev0`; README continues to install verified release v0.1.15.

## Verification

- Add AppTest coverage for the exact compact table header and detail facts.
- Require that concern text remains visible in Criterion Detail.
- Run Ruff, all offline tests, and the deterministic benchmark.
- Build and clean-install one wheel; verify version identity, installed benchmark, dependency
  consistency, web health, and packaged browser state.
- Compare before and after at the same viewport and analyzed-demo state; inspect console errors.
