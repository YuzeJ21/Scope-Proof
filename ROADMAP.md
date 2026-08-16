# ScopeProof Roadmap

ScopeProof v0.2 is a reviewer-first public alpha. The deterministic engine, local workbench, CLI,
exports, benchmark, packaging, and protected CI are engineering evidence only. They do not prove
runtime correctness, adoption, or beta readiness.

This roadmap separates owner-led productization from external validation. Stage 1 is
`closed_not_pursued_by_owner` with all external-evidence counts at zero. Stage 2 is
`owner_led_productization_active`; this owner decision does not create customer validation.

## Current release and validation state

The GitHub Release record is authoritative for publication availability.
ScopeProof v0.2.3 is published. Public install: v0.2.3 is available from the
[v0.2.3 GitHub Release](https://github.com/YuzeJ21/Scope-Proof/releases/tag/v0.2.3),
which provides the wheel, source archive, and checksum manifest.

| Area | Current state |
|---|---|
| Published install | v0.2.3 GitHub Release with wheel, source archive, and checksum manifest |
| Active source line | Unreleased `0.2.4.dev0`; no v0.2.4 release, tag, or package publication exists |
| Post-PR #193 resulting-main snapshot (2026-08-13) | PR #193 product-source baseline at `432371c4faec0b790f70fec32b4d3fc4d5132cfa` (PR head `8bb407079a0ff7098d2fc18af3d75b216725df2e`, base `9426e8714ffd2c3742bb074ae26fc788f1049c63`) |
| Verified product baseline | PR #184 release integration landed on `main` at `448c42758ea139bf9203cbf1bb04b02b02ae412c` |
| Product verification | Full product-code verification is bound to `fb74d4bbb402f4de3e2fabb56ce28c948214f8c2`; package, install, installed-benchmark, and health artifacts are bound to `81598899fcd85df58ab22f9212f2e8382f4a5e5f`. |
| Release integration evidence | PR #184 release integration at `448c42758ea139bf9203cbf1bb04b02b02ae412c`; exact-main CI, CodeQL, and Pages all succeeded, and `origin/main` matched at the 2026-08-08 branch-start snapshot |
| Integration authority | PR #184 exact-main CI run `30854382641`, CodeQL run `30854382413`, and Pages run `30854382659` verify the release integration |
| Historical source integration | PR #183 integrity/reviewer-loop source merge at `cd362a85a558645a0f56d6540f6bf035e5821809`; runs `30847416893`, `30847415556`, and `30847417705` remain historical source-integration evidence |
| Snapshot verification | Hosted resulting-main CI run [`31704668247`](https://github.com/YuzeJ21/Scope-Proof/actions/runs/31704668247) at exact PR #193 tree `432371c4faec0b790f70fec32b4d3fc4d5132cfa` recorded 2,251 passed, 2 intentional skips, and 95.22% coverage |
| Snapshot engineering checks | Resulting-main CI run [`31704668247`](https://github.com/YuzeJ21/Scope-Proof/actions/runs/31704668247) covers Python 3.11, Python 3.13, Windows, installed-wheel, deterministic benchmark, and packaged-browser checks; CodeQL run [`31704666031`](https://github.com/YuzeJ21/Scope-Proof/actions/runs/31704666031) and Pages run [`31704668164`](https://github.com/YuzeJ21/Scope-Proof/actions/runs/31704668164) also succeeded |
| Product validation | Stage 1 closed as not pursued with every count at zero; owner-led Stage 2 is active without customer-validation claims |

Verify live GitHub and current release records before relying on publication state. Engineering
milestones may proceed through owner-led Stage 2, but they remain engineering evidence rather than
customer validation.

After the v0.2.3 release, PR #185 merged core-backed CLI lifecycle parity and packaged Chromium
proof at `30177733ef312ced22e6a2e57e3df6fdb1e92507`; PR #187 merged Python 3.13 plus bounded
keyboard/focus and zoom engineering evidence at `c548759b5464ad5bb98baf1e996397f241dfc455`; and
PR #188 merged verified-public provenance enforcement at
`077f9351283b319b82854ad1df95eac7ce614e21`. CLI lifecycle parity is implemented;
verified-public provenance enforcement is implemented. These changes form the `0.2.4.dev0`
development line and earn no Stage 1 credit.

PR #189 established the post-release development identity; PR #190 preserved comparison
relationship integrity; PR #191 remediated the GitPython dependency and security issue; PR #192
bounded same-origin GitHub pagination; and PR #193 hardened cross-platform identity-bound alpha
storage. The dated post-PR #193 resulting-main snapshot at
`432371c4faec0b790f70fec32b4d3fc4d5132cfa` is the PR #193 product-source baseline, not a
declaration of perpetually current `main`. These are engineering changes on `0.2.4.dev0`, not a
new published release; v0.2.3 remains the published release and none earns Stage 1 credit.

### Verification and evidence boundaries

- Engineering checks do not prove acceptance-criteria correctness.
- CI Windows evidence is not a real Windows desktop workflow.
- Browser automation is not screen-reader or WCAG-conformance evidence.
- Reviewer identity remains asserted, not authenticated.
- The GitHub Action remains opt-in and informational. Its neutral-only
  `ScopeProof evidence summary (informational)` is exact-head and criteria-source bound, is not a
  required branch-protection check, and does not create customer validation. It does not prove
  correctness, does not prove runtime behavior, does not prove accessibility, and does not prove
  demand or adoption. Stage 1 remains at 0/5 qualifying reviews, 0/3 independent practitioners,
  0/3 public repositories, 0/3 independently observed under-ten-minute completions, and 0/2
  reuse-intent signals.
- ScopeProof never executes target-repository code.

### Storage-maintenance boundary

`atomic_files.py` is large and transactionally complex, and its existing regression coverage is
strong. Portable storage may fail closed on filesystems without required hard-link behavior, and
ambiguous filesystem ownership must be preserved rather than deleted. Future filesystem-behavior
changes require a separate design, test-first decomposition, and owner approval; do not weaken
identity-bound cleanup or atomicity to simplify the implementation.

## Stage 0 — Reviewer-first product reset

Status: prior PR #177 repairs remain historical engineering evidence. PR #180
merged the exact-head runtime-evidence repair, PR #181 aligned the
documentation, PR #182 merged product convergence, and PR #183 merged the
integrity/reviewer-loop source work. PR #184 then merged the v0.2.3 release
integration at `448c42758ea139bf9203cbf1bb04b02b02ae412c`; the peeled tag and
release baseline resolve to the same commit. `origin/main` also matched at the
2026-08-08 branch-start snapshot. The GitHub Release record is
authoritative for publication availability. None of this engineering evidence
advances Stage 1, which remains at zero.

- [x] Acceptance-coverage vocabulary separates candidate strength from reviewer decisions.
- [x] Standard flow is public PR → confirmed criteria → coverage → decisions → export.
- [x] Live reviews and genuine-alpha records require an explicit verified-public repository fact;
  private, ambiguous, and legacy-unverified sources fail closed for Stage 1.
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
R-002 is engineering evidence only. It contributes to owner-led engineering work but not customer
validation or optional external-discovery evidence.

## Current engineering track — v0.2.3 Evidence Quality

Status: the earlier candidate and PR #177 repairs remain merged history. PR #179
merged the first workbench UX change, PR #180 merged exact-head runtime-evidence
hardening, PR #181 aligned post-merge documentation, PR #182 merged product
convergence, and PR #183 merged the integrity/reviewer-loop source work at
`cd362a85a558645a0f56d6540f6bf035e5821809`. PR #184 merged the published
v0.2.3 release integration at `448c42758ea139bf9203cbf1bb04b02b02ae412c`.
The GitHub Release record is authoritative for publication availability. This
engineering and release work earns zero Stage 1 credit.

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
- [x] Fail closed when GitHub provides no inspectable changed-file patch instead
  of treating a missing patch as a complete empty file.
- [x] Restore saved-review source identity for a one-click current-head check,
  connect matrix cards to criterion detail, and require a note for acceptance
  below the required candidate-evidence level.
- [x] Make all five re-review candidate classes inspectable in the workbench and
  add validated comparison Markdown and JSON downloads.
- [ ] Freeze a new holdout before using it to evaluate a retrieval algorithm change. R-003 design
  is complete; cohort generation and later criteria and label confirmations remain distinct
  evidence-integrity gates.
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
The merged PR #182 convergence source and its deliberately separated
historical-candidate exact-target evidence are recorded in the
[product-convergence verification audit](docs/audits/v0.2.3-product-convergence/verification.md).
The merged PR #183 ingestion and reviewer-loop source evidence is recorded in the
[integrity and reviewer-loop verification audit](docs/audits/v0.2.3-integrity-reviewer-loop/verification.md).

## Stage 1 — Genuine public alpha

Status: `closed_not_pursued_by_owner`.

Stage 1 did not pass. On 2026-08-14, the owner chose not to pursue the external public-alpha
program. Closure changes no measured count, satisfies none of the former exit conditions, and
creates no customer, adoption, usability, timing, reuse, demand, pricing, or willingness-to-pay
evidence.

Current measured state:

- 0/5 qualifying reviews.
- 0/3 independent practitioners.
- 0/3 public repositories.
- 0/3 independently observed under-ten-minute completions.
- 0/2 reuse-intent signals.
- Zero participant False Ready observations across zero participant reviews; this is
  not a validated False Ready rate.

Former exit conditions, preserved as unmet historical targets:

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

The [concierge host checklist](docs/alpha/concierge-host-checklist.md) remains available only for
optional voluntary external feedback. Using it does not reopen Stage 1 or create stage credit.

### Archived external-evidence distinctions

These distinctions remain binding if optional external research is separately authorized:

- Preparation is not outreach: prepare public, source-safe materials and qualification records
  before contacting anyone, but do not contact, recruit, or message a participant without that
  separate authorization.
- Inbound submissions are not recruited participants: retain the source and authorization path for
  each case and do not count an inbound lead as recruited use.
- Observed completion evidence is not self-reported timing: independently observe the complete
  review-to-inspectable-coverage-report interval before crediting the under-ten-minute count.
- Qualifying reviews are not demos, tests, maintainers, bots, or repository activity: only the
  documented non-owner, public-PR, source-owner-confirmed, exact-head, saved-review, validated-
  outcome path can credit a count.

## Stage 2 — Owner-led productization

Status: `owner_led_productization_active`.

The owner authorized owner-led productization on 2026-08-14. This status does not claim customer
validation. Work may improve product and workflow clarity, deterministic evidence quality,
fail-closed lifecycle integrity, packaging, installation, compatibility, accessibility
engineering, documentation, public official-source research, and release readiness.

The [Stage 2 productization packet](docs/commercialization/stage2-readiness-packet.md) is the
operating boundary. External commercial discovery is optional and separate from owner-led
productization. It is not required to continue Stage 2 and needs separate owner authorization
before outreach or participant contact.

Stage 2 does not authorize a merge, release, tag, package publication, outreach, participant
contact, R-002 retuning, R-003 generation, billing, accounts, private-repository support, hosted
source processing, generic code review, security scanning, automatic fixes, or paid APIs.

The [30-day Design Partner Sprint](docs/commercialization/design-partner-sprint.md) is an optional
research protocol, not a productization gate. The
[market-positioning hypotheses](docs/commercialization/market-positioning-hypotheses.md) remain
unvalidated hypotheses unless genuine attributable evidence is later collected.

## Stage 3 — Limited beta

Status: gated by a separate owner decision after Stage 2 engineering evidence is reviewed.

Stage 3 may define a bounded release candidate or beta only through a new owner-authorized plan.
Owner-led productization cannot be presented as customer validation, and no release, tag, or
publication is implied by Stage 2 progress.

Exit conditions:

- Repeat use occurs on a later PR without project-owner prompting.
- Reviewers can explain and act on candidate status without mistaking it for correctness.
- Re-review comparison is used to inspect a changed head rather than relying on stale evidence.
- Repeated friction is classified by source loading, criteria, coverage, decisions, export, or
  integration.
- Product changes are traceable to genuine observations and have regression coverage.
- Confirmed False Ready remains zero.

## Stage 4 — Evidence-guided expansion decision

Status: gated by a separate owner decision and evidence appropriate to the proposed expansion.

Only recurring behavior can justify broader scope. Candidate directions include clearer
requirements intake, better evidence explanations, and narrower collaboration handoffs. Private
repositories, billing, accounts, generic code review, security scanning, automatic fixes, and paid
LLM APIs require a separate owner decision and are not implied by beta progress.

Stage 4 requires a named constraint, evidence appropriate to that constraint, and separate owner
approval. Missing external evidence remains missing; engineering work does not turn into customer
evidence.

## Honest stop and pivot rules

- Do not create synthetic validation, invented users, or constructed outcomes.
- Do not create recurring external-evidence monitors merely to manufacture activity.
- Do not execute pull-request code or promote implementation evidence to test or runtime proof.
- Do not weaken deterministic gates to improve apparent completion.
- Do not broaden the evaluation-only use policy without a new explicit owner decision.
- If optional genuine sessions occur, preserve negative and incomplete results without rewriting
  them as productization success.
