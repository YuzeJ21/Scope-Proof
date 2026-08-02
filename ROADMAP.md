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
| Verified product baseline | v0.2.3 product-convergence candidate through `fb74d4bbb402f4de3e2fabb56ce28c948214f8c2`; untagged and unreleased |
| Product verification | Full product-code verification is bound to `fb74d4bbb402f4de3e2fabb56ce28c948214f8c2`; package, install, installed-benchmark, and health artifacts are bound to `81598899fcd85df58ab22f9212f2e8382f4a5e5f`. |
| Pre-convergence main baseline | PR #181 merged documentation-only post-merge alignment as `eaa66c5979e2a71769d58f0699537da474094d06`; repository-tree CI, CodeQL, and Pages succeeded |
| Integration authority | Protected-PR `verify` and CodeQL plus resulting-main CI and Pages. GitHub history is authoritative for the final merge SHA; publication remains a separate decision. |
| Product validation | Stage 1 waiting at zero; Stages 2–4 gated |

Verify live GitHub and current release records before relying on publication state. Engineering
milestones can proceed while Stage 1 waits, but they do not advance product-validation stages.

## Stage 0 — Reviewer-first product reset

Status: prior PR #177 repairs remain historical engineering evidence. PR #180
merged the exact-head runtime-evidence repair, and PR #181 aligned the
documentation. The later product-convergence candidate has independent local
core, package, browser, and static-site evidence. GitHub's protected PR and
resulting-main workflow records determine its integration status. None of this
establishes release assets, checksums, a tag, a GitHub Release, or Stage 1
evidence.

- [x] Acceptance-coverage vocabulary separates candidate strength from reviewer decisions.
- [x] Standard flow is public PR → confirmed criteria → coverage → decisions → export.
- [x] Enforce at the core boundary that manual verification records runtime
  evidence and its decision atomically, and reject unpaired reconstructed
  bundles or states at every trusted boundary.
- [x] Enforce at the core boundary that final acceptance requires complete
  ingestion, passing observed CI, and a current accepted decision for every
  criterion.
- [x] Encode unchanged-candidate paths, transmit the exact head SHA separately,
  and reject malformed or unanchored candidate responses.
- [x] Bind every effective E3/E4 manual decision to one immutable runtime
  evidence ID and matching repository, PR, head, criterion, reviewer, and level.
- [x] Migrate version 1/2 records to version 3 without inventing manual links;
  legacy-unlinked decisions remain auditable and require reconfirmation.
- [x] Bind each new criteria confirmation to an immutable source URI, optional
  revision, exact source-text digest, ordered normalized-criteria digest,
  confirmer, and timestamp. Version 1–3 records migrate to version 4 without
  invented provenance and remain fail-closed until reconfirmed.
- [x] Project runtime identity through the workbench and JSON, Markdown, CSV,
  and HTML exports while retaining Pydantic validation.
- [x] Project criteria-source provenance through the CLI, advanced Action,
  workbench, alpha record, local persistence, and all validated exports.
- [x] Reject malformed or cross-object gate input deterministically before it
  can be evaluated, including duplicate identifiers, coverage mismatches,
  foreign resolution identifiers, and provenance-digest contradictions.
- [x] Bind qualifying alpha outcomes to a fully revalidated saved review,
  genuine public-GitHub origin, exact PR head, criteria snapshot, and immutable
  one-time outcome; fixture, demo, research, and legacy-unknown origins remain
  ineligible.
- [x] Provide an offline confirmation-preparation command that calculates
  exact requirement hashes, refuses overwrite, and never needs a paid API.
- [x] Simplify the workbench and public-alpha surfaces with supported theme
  settings and progressive disclosure while preserving safety copy, focus
  treatment, and deterministic gate behavior.
- [x] Clean the public product page for desktop and narrow screens, including a
  readable mobile header and a valid local favicon without changing the
  evidence boundary.
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

Status: the earlier candidate and PR #177 repairs remain merged history. PR #179
merged the first workbench UX change, PR #180 merged exact-head runtime-evidence
hardening, and PR #181 aligned post-merge documentation. The later verified
product-convergence candidate adds criteria-source provenance, stricter trusted
boundaries, genuine-origin alpha qualification, and cleaner product surfaces.
GitHub history determines whether its protected integration has completed. The
source is not tagged or released. This work earns zero Stage 1 credit.

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
- [x] Reject ineligible final-acceptance and unpaired manual-verification
  events in the core lifecycle, with regression coverage.
- [x] Preserve exact-head candidate retrieval across URL metacharacters and
  Unicode paths, with request-level regression coverage.
- [x] Require immutable runtime identity for new E3/E4 records and fail closed
  on duplicate, missing, foreign-repository, wrong-PR, wrong-head, or mismatched
  resolution links.
- [x] Keep legacy runtime history visible while deterministically requiring
  active-head reconfirmation instead of guessing an association.
- [x] Show complete passing CI observations with skipped checks as an explicit
  visible limitation without changing their deterministic check state.
- [x] Restore autosave recovery for bundle-less revised reviews with stale
  criterion-detail drafts, without mutating review state or enabling exports
  before reanalysis.
- [x] Require an exact, typed criteria-source snapshot before new analysis,
  automated review, export, alpha outcome, or final acceptance can proceed.
- [x] Preserve legacy version 1–3 records without fabricating provenance and
  require explicit source reconfirmation before they can regain eligibility.
- [x] Reduce first-use and public-alpha page density without hiding evidence,
  limitations, labels, controls, or the reviewer confirmation step.
- [ ] Freeze a new holdout before using it to evaluate a retrieval algorithm change. R-003 design
  is complete, but cohort generation awaits a separate explicit owner approval.
- [x] Complete fresh packaging, clean-install, and a bounded accessibility and platform audit in
  the available environment before calling v0.2.3 an internal release candidate; unsupported
  environments and interactions remain explicitly unverified.
- [x] Keep publication as a separate owner-controlled decision.

Do not retune against the frozen R-002 cohort, weaken thresholds, add model-generated verdicts, or
promote search diagnostics into evidence or correctness claims.

Current product, gap, and next-stage details are maintained in the
[v0.2.3 status audit](docs/releases/v0.2.3-status-and-next-stages.md). Current official-source
competitive research is maintained separately in the
[current official-source market comparison](docs/commercialization/market-comparison-2026-07-26.md).
Historical current-main package, security, and environment evidence is recorded
in the [post-merge release-readiness audit](docs/releases/v0.2.3-post-merge-release-readiness.md).
The merged product-tree evidence is recorded in the
[exact-head verification audit](docs/audits/exact-head-runtime-evidence/verification.md).
The later convergence candidate and its deliberately separated exact-target
evidence are recorded in the
[product-convergence verification audit](docs/audits/v0.2.3-product-convergence/verification.md).

## Stage 1 — Genuine public alpha

Status: `waiting_for_inbound_public_alpha_submission`; Stage 1 remains zero.
The Stage 0 engineering foundation is restored, but no genuine qualifying
submission exists.

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
