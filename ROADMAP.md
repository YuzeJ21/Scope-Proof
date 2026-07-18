# ScopeProof Roadmap

ScopeProof v0.2 is a reviewer-first public alpha. The deterministic engine, local workbench, CLI,
exports, benchmark, packaging, and protected CI are engineering evidence only. They do not prove
runtime correctness, adoption, or beta readiness.

This roadmap advances on genuine use evidence, not elapsed time, releases, stars, downloads, or
automated activity. The current external state is
`waiting_for_external_participant_evidence`.

## Stage 0 — Reviewer-first product reset

Status: complete when v0.2.0 release verification passes.

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

## Stage 1 — Genuine public alpha

Status: waiting for external participant evidence.

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

## Stage 2 — Limited beta

Entry requires every Stage 1 condition. The beta remains supervised and public-repository-only.

Exit conditions:

- Repeat use occurs on a later PR without project-owner prompting.
- Reviewers can explain and act on candidate status without mistaking it for correctness.
- Re-review comparison is used to inspect a changed head rather than relying on stale evidence.
- Repeated friction is classified by source loading, criteria, coverage, decisions, export, or
  integration.
- Product changes are traceable to genuine observations and have regression coverage.
- Confirmed False Ready remains zero.

## Stage 3 — Evidence-guided expansion decision

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
