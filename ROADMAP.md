# ScopeProof Roadmap

ScopeProof is currently an **engineering-complete public alpha**. Its deterministic review engine,
local workbench, CLI, exports, regression benchmark, packaging, and protected CI are operational.
That engineering evidence does not establish product adoption, runtime correctness for a reviewed
pull request, or beta readiness by itself.

This roadmap advances on evidence, not elapsed time or activity volume.

## Stage 1 — Beta-entry preparation

Status: in progress.

Exit conditions:

- [x] Release artifacts can be installed and checked without a source checkout.
- [x] The declared Python 3.11 minimum and the primary Python 3.12 path run the full test and
  benchmark gates in CI.
- [x] Markdown, JSON, CSV, and HTML exports are documented.
- [x] Public contribution, security, launch, and evidence-boundary guidance is available.
- [ ] At least one genuine public pull request is reviewed against source-owner-confirmed criteria.
- [ ] The source owner records whether the report found a useful pre-merge gap, produced only known
  information, or created friction.
- [x] **Software license decision:** the repository owner chose an evaluation-only use policy and
  explicitly records that no open-source license is granted.

Activation readiness is now available through the [ten-minute participant quickstart](docs/alpha/participant-quickstart.md), public-PR qualification checklist, explicit source-owner confirmation in the workbench and CLI, and consent-gated local alpha-case records. These tools make the two remaining gates auditable; they do not satisfy either gate without a genuine participant and outcome.

The repository owner uses the
[concierge host checklist](docs/alpha/concierge-host-checklist.md) as the operational index for a
manually recruited supervised trial; the checklist does not itself satisfy either external gate.

## Stage 2 — Limited beta

Entry requires every open Stage 1 condition. Limited beta means repeated, supervised use on public
repositories; it does not mean the evidence assistant is a correctness oracle.

Exit conditions:

- More than one genuine reviewer completes the confirmed-criteria workflow on a real public PR.
- Review records preserve immutable head SHAs, explicit limitations, and human outcomes.
- Repeated friction is classified by product stage: discovery, criteria confirmation, evidence
  review, resolution, export, or integration.
- Any product change is linked to observed evidence and has regression coverage.
- False Ready remains zero in the checked-in must-have benchmark corpus.

## Stage 3 — Beta expansion decision

Only recurring evidence can justify broader scope. Candidate directions include better requirement
intake, improved evidence explanation, or a narrower team workflow. Private repositories, billing,
generic code review, security scanning, automatic fixes, and paid LLM APIs remain out of scope until
the owner makes a separate explicit product decision.

## Honest stop and pivot rules

- Do not create synthetic validation, invented users, or constructed outcomes to satisfy a stage
  gate.
- No recurring monitor should poll for evidence when nothing new exists. Record the exact waiting
  condition once, then continue with another independent, evidence-backed maintenance slice.
- Do not execute pull-request code or promote static candidates to test or runtime verification.
- Do not broaden or replace the recorded evaluation-only use policy without a new owner decision.
- Do not refactor large modules solely to create activity; use a demonstrated defect or repeated
  maintenance cost to define the slice.

## Current external waiting conditions

1. A source owner must confirm the normalized acceptance criteria for a genuine public PR.
2. A human reviewer must record the outcome after reviewing ScopeProof's report.

Until those events occur, engineering work can improve verified compatibility, documentation,
onboarding, and defects found through real product use, but it cannot truthfully close the beta
entry gate.
