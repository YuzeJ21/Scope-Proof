# ScopeProof Roadmap

ScopeProof v0.2 is a reviewer-first public alpha. The deterministic engine, local workbench, CLI,
exports, benchmark, packaging, and protected CI are engineering evidence only. They do not prove
runtime correctness, adoption, or beta readiness.

This roadmap advances on genuine use evidence, not elapsed time, releases, stars, downloads, or
automated activity. The current external state is
`waiting_for_inbound_public_alpha_submission`.

## Current release and validation state

| Area | Current state |
|---|---|
| Published install | v0.2.1 |
| Active source candidate | v0.2.3, internal and unpublished |
| Public `main` | Does not contain the active local R-002 and v0.2.3 engineering line |
| Current engineering track | v0.2.3 Evidence Quality; implementation complete, verification in progress |
| Product validation | Stage 0 complete; Stage 1 waiting; Stages 2–4 gated |

Verify live GitHub and current release records before relying on publication state. Engineering
milestones can proceed while Stage 1 waits, but they do not advance product-validation stages.

## Stage 0 — Reviewer-first product reset

Status: complete.

- [x] Acceptance-coverage vocabulary separates candidate strength from reviewer decisions.
- [x] Standard flow is public PR → confirmed criteria → coverage → decisions → export.
- [x] External verification records runtime evidence and its decision atomically.
- [x] Final acceptance requires complete ingestion, passing observed CI, and a current accepted
  decision for every criterion.
- [x] Optional alpha feedback stays separate, local, consent-controlled, and off by default.
- [x] Re-review comparison preserves both bundles and reports head, evidence, decision, and status
  changes.
- [x] The GitHub Action remains an advanced, non-default preview.
- [x] **Software license decision:** the evaluation-only use policy remains unchanged and no
  open-source license is granted.

## Completed engineering evidence — does not advance Stage 1

- [x] R-001 records a hash-bound public-PR engineering comparison with corrected observed-CI
  aggregation and explicit E2 eval-definition intent. It does not establish test execution,
  runtime verification, acceptance, or Stage 1 credit.
- [x] R-002 records a deterministic 20-case, 12-repository static baseline with frozen
  benchmark-owner research criteria and labels, immutable references, zero unexpected Ready
  outcomes, and two identical offline runs.
- [x] R-002 executed 20/20 cases with zero failures, skipped cases, or rerun mismatches. It
  recorded 18/22 benchmark-label candidate precision, 5/20 criterion candidate coverage, and
  41/41 missing-evidence explanation completeness.

These cases, repositories, outcomes, and timing contribute zero genuine Alpha reviews,
participants, repositories, timing observations, False Ready rate evidence, or reuse signals.
R-002 is engineering evidence only. Stages 2–4 remain gated.

## Current engineering track — v0.2.3 Evidence Quality

Status: implementation complete; internal-candidate verification in progress. This work can proceed while Stage 1 waits but
does not advance Stage 1.

- [x] Add validated retrieval outcomes and one deterministic diagnostic per criterion.
- [x] Record searched terms, identifiers, paths, evidence types, inspected-line counts, filtering
  counts, and accepted-candidate counts without changing retrieval behavior.
- [x] Persist diagnostics in new reviews while preserving historical reviews without inventing
  diagnostics.
- [x] Render diagnostics in the workbench, CLI-created reviews, constructed demo, and Markdown,
  JSON, CSV, and HTML exports.
- [x] Prove existing evidence IDs, scores, references, findings, and gate decisions are unchanged.
- [x] Prove the completed R-002 canonical inputs and result remain byte-identical.
- [x] Classify R-002 misses only after diagnostics exist. Convert genuine retrieval defects into
  separate constructed regression fixtures.
- [ ] Freeze a new holdout before using it to evaluate a retrieval algorithm change. R-003 design
  is complete, but cohort generation awaits a separate explicit owner approval.
- [x] Complete fresh packaging, clean-install, accessibility, and available-platform verification
  before calling v0.2.3 an internal release candidate.
- [ ] Keep publication as a separate owner-controlled decision.

Do not retune against the frozen R-002 cohort, weaken thresholds, add model-generated verdicts, or
promote search diagnostics into evidence or correctness claims.

Current product, gap, and next-stage details are maintained in the
[v0.2.3 status audit](docs/releases/v0.2.3-status-and-next-stages.md). Current official-source
competitive research is maintained separately in the
[2026-07-26 market comparison](docs/commercialization/market-comparison-2026-07-26.md).

## Stage 1 — Genuine public alpha

Status: `waiting_for_inbound_public_alpha_submission`.

Current measured state:

- 0/5 qualifying reviews.
- 0/3 independent practitioners.
- 0/3 represented public repositories.
- 0/3 independently observed under-ten-minute completions.
- 0/2 reuse-intent signals.
- Zero participant False Ready observations across zero participant reviews; this is not a
  validated False Ready rate.

All exit conditions are required:

- [ ] Five completed reviews on genuine public pull requests.
- [ ] At least three independent practitioners across product, QA, or engineering roles.
- [ ] At least three public repositories.
- [ ] At least three participants reach an inspectable coverage report within ten minutes.
- [ ] Misleading candidate matches and material friction are recorded, not hidden.
- [ ] Zero confirmed False Ready outcomes.
- [ ] At least two independent participants state an intent to use ScopeProof again.

Only source-owner-confirmed criteria from public requirements, a genuine public pull request, an exact reviewed head SHA, a saved
review, and a validated local outcome record count. Constructed demos, owner-authored synthetic
cases, technical smokes, release downloads, and GitHub activity do not count.

The [concierge host checklist](docs/alpha/concierge-host-checklist.md) indexes the optional manual
research path. It helps collect evidence but does not satisfy any gate by itself.

## Stage 2 — Commercial discovery

Status: gated; do not begin commercial claims or productization until every Stage 1 condition is
met.

Entry requires every Stage 1 condition. The current free, public-repository-only design-partner
review remains research; no paid product or billing is active.

All exit conditions are required before considering a separate Local Pro product decision:

- At least two independent completed participants explicitly intend to use ScopeProof on another
  PR.
- At least two independent completed participants voluntarily agree to discuss the team-price hypothesis
  after genuine product use.
- A useful result occurs before approval, after a new commit, or during an acceptance or release
  decision.
- Zero confirmed False Ready outcomes remain.
- All misleading candidates and material friction remain recorded.

These signals are not revenue, orders, customers, paid demand, or willingness to pay.
Local Pro remains deferred, including private-repository ingestion, commercial licensing, billing, hosted source
processing, accounts, integrations, and enterprise capabilities. See the
[30-day Design Partner Sprint](docs/commercialization/design-partner-sprint.md) for the canonical
research workflow and stop gates. The
[market-positioning hypotheses](docs/commercialization/market-positioning-hypotheses.md) record the
current adjacent alternatives, likely-user and likely-buyer hypotheses, adoption risks, and trust
requirements. Genuine completed reviews are required to validate or reject them.

## Stage 3 — Limited beta

Status: gated; requires Stages 1–2, genuine repeat use, and a separate owner decision.

Entry requires every Stage 1 and Stage 2 condition plus a separate owner decision. The beta
remains supervised and public-repository-only unless that decision explicitly changes the scope.

Exit conditions:

- Repeat use occurs on a later PR without project-owner prompting.
- Reviewers can explain and act on candidate status without mistaking it for correctness.
- Re-review comparison is used to inspect a changed head rather than relying on stale evidence.
- Repeated friction is classified by source loading, criteria, coverage, decisions, export, or
  integration.
- Product changes are traceable to genuine observations and have regression coverage.
- Confirmed False Ready remains zero.

## Stage 4 — Evidence-guided expansion decision

Status: gated; only repeated genuine behavior may justify expansion.

Only recurring behavior can justify broader scope. Candidate directions include clearer
requirements intake, better evidence explanations, and narrower collaboration handoffs. Private
repositories, billing, accounts, generic code review, security scanning, automatic fixes, and paid
LLM APIs require a separate owner decision and are not implied by beta progress.

## Honest stop and pivot rules

- Do not create synthetic validation, invented users, or constructed outcomes.
- No recurring monitor should run when no new external evidence exists; record the waiting state
  once and continue independent maintenance.
- Do not execute pull-request code or promote implementation evidence to test or runtime proof.
- Do not weaken deterministic gates to improve apparent completion.
- Do not broaden the evaluation-only use policy without a new explicit owner decision.
- If repeated genuine sessions show no useful gap or no reuse intent, narrow or stop the product
  rather than substituting release polish for demand.
