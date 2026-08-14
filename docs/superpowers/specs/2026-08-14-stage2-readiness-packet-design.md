# Stage 2 Readiness Packet Design

## Context

ScopeProof's Stage 0 engineering foundation is complete, but Stage 1 has no genuine participant
evidence. Its measured state remains `waiting_for_inbound_public_alpha_submission` at 0/5
qualifying reviews, 0/3 independent practitioners, 0/3 public repositories, 0/3 independently
observed under-ten-minute completions, and 0/2 reuse-intent signals. Zero participant False Ready
observations across zero participant reviews is not a validated False Ready rate.

The owner has chosen to pause active Stage 1 work and prepare Stage 2 materials without claiming
that Stage 1 passed or that Stage 2 began. Pausing changes the operating posture, not the measured
evidence. It does not create a participant, review, repository, timing observation, reuse signal,
commercial signal, or permission to contact anyone.

Existing commercialization documents contain useful hypotheses and a future design-partner
workflow, but the activation boundary is distributed across the roadmap, the 30-day design-partner
sprint, and the market-positioning hypotheses. A single readiness packet will make the future
research path reviewable without adding product behavior or manufacturing activity.

## Decision

Create one authoritative, docs-only Stage 2 readiness packet. It prepares a future post-use
commercial-discovery workflow while keeping Stage 2 explicitly not started.

The packet will use two separate status fields:

- **Measured product-validation state:**
  `waiting_for_inbound_public_alpha_submission`, with every Stage 1 count unchanged at zero.
- **Owner operating posture:** Stage 1 paused; Stage 2 readiness materials only; Stage 2 not
  activated.

The distinction prevents a pause from being mistaken for completion and prevents prepared research
materials from being mistaken for executed discovery.

## Documentation architecture

Add `docs/commercialization/stage2-readiness-packet.md` as the sole operational index for future
Stage 2 preparation. It will link to, rather than duplicate, the current design-partner sprint and
market-positioning hypotheses.

Update the current-facing Stage sections in `ROADMAP.md` to state the owner operating posture and
link to the readiness packet. Preserve all Stage 1 counts, exit conditions, and Stage 2 entry gates.
Do not rewrite historical release audits or imply that the pause changes published v0.2.3 or the
unreleased `0.2.4.dev0` development identity.

Add a focused repository contract that reads the authoritative Stage 1 and Stage 2 sections, not
the entire document, and requires:

- all five current Stage 1 measurements at zero;
- the zero-participant False Ready limitation;
- explicit Stage 1 paused operating posture;
- explicit Stage 2 readiness-only and not-started wording;
- every Stage 1 exit condition plus separate owner authorization before Stage 2 activation; and
- the readiness packet's non-authorization and no-outreach boundaries.

The contract must fail when a protected statement is removed from its authoritative section even
if similar text remains elsewhere in the repository.

## Readiness packet contents

### 1. Status and activation gate

The opening block will show the exact zero counts and state that Stage 1 is paused, not passed.
Stage 2 may activate only after every Stage 1 exit condition is supported by genuine evidence and
the owner separately authorizes Stage 2.

Prepared documents, tests, demos, CI, releases, downloads, issue activity, owner rehearsals, and
elapsed time earn no Stage 1 or Stage 2 credit.

### 2. Post-use discovery guide

The guide will remain dormant until every Stage 1 exit condition has genuine evidence and the owner
separately authorizes Stage 2. One qualifying public review is necessary evidence but cannot
activate the guide. After activation, it will ask, in order:

1. What workflow would the participant otherwise have used?
2. What attributable result, if any, did ScopeProof expose?
3. Did the result change, clarify, confirm, or have no effect on a decision?
4. Which step created the most material friction?
5. Did the participant understand candidate evidence versus correctness and runtime proof?
6. Would the participant independently bring another public pull request?
7. Would the participant voluntarily discuss the research-only team-price hypothesis?

The guide will not solicit names, email addresses, employers, private repositories, confidential
requirements, customer data, payment data, purchase authorization, or sales-contact permission.

### 3. Hypothesis ledger

The packet will keep each hypothesis separate from evidence:

- primary user: product manager, QA practitioner, or engineer;
- likely buyer: QA, engineering, product operations, or product leadership;
- job: pre-merge acceptance-evidence review at an immutable head;
- alternative: manual checklist, spreadsheet, lifecycle suite, test management, or human/AI code
  review;
- value: attributable useful gap, clearer decision, or current evidence after a changed head;
- adoption risk: setup, criteria confirmation, public-only scope, unresolved output, or workflow
  cost;
- reuse: explicit post-use intent only; and
- pricing: USD 99 per team per month and USD 999 per team per year as research anchors only.

Every row will start as `unknown`. A hypothesis may become `supported`, `mixed`, or `disconfirmed`
only from attributable completed-use evidence. Silence, refusal, owner opinion, or activity metrics
will not change its state.

### 4. Evidence-capture template

Use a Markdown template rather than a new application schema, form, database, or tracking service.
For each future completed review it will record:

- public case reference and exact reviewed head;
- participant role category without direct identifiers;
- source-owner confirmation path;
- completed-review and validated-outcome references;
- independently observed completion-time band, when genuinely observed;
- alternative workflow;
- attributable result and decision impact;
- largest friction category;
- candidate-versus-proof understanding;
- reuse response;
- optional price-discussion response; and
- evidence source plus `unknown`, `declined`, or `not observed` where applicable.

The template is preparation only. It will contain no invented example response that could be
mistaken for a participant record, and it will not be wired into the product's saved-review store.

### 5. Decision rules

The packet will preserve explicit future outcomes:

- **Continue** only while completed genuine use exposes attributable value, the evidence boundary
  is understood, and confirmed False Ready remains zero.
- **Narrow** when one observed workflow step repeatedly creates most of the friction.
- **Pivot** when participants consistently prefer a different job or existing alternatives are
  sufficient.
- **Stop** when fewer than two of five completed sessions are useful or decision-relevant, nobody
  intends repeat use, or confirmed False Ready cannot remain zero.

No decision may be calculated while the qualifying denominator is zero.

## Data flow and failure behavior

The future evidence path is:

`qualifying Stage 1 review -> participant-selected outcome -> validated Stage 1 evidence ->`
`all Stage 1 gates pass -> separate owner authorization -> Stage 2 interview -> hypothesis update`

If any prerequisite is absent, ambiguous, private, self-reported where independent observation is
required, or not attributable to completed use, the flow stops. The field remains `unknown`,
`declined`, or `not observed`; no positive signal is inferred. Prepared questions remain dormant.

The readiness packet cannot authorize outreach, activate a recurring monitor, open recruitment
issues, post announcements, contact participants, or start commercial claims. Those are separate
owner and evidence gates.

## Alternatives considered

- Leave the current documents unchanged: rejected because the activation gate and future research
  workflow remain fragmented and easier to misread.
- Build forms, tracking, or discovery automation now: rejected because no qualifying participant
  evidence exists and new tooling would manufacture activity without validating the job.
- Remove the Stage 1 dependency from Stage 2: rejected because it would allow hypothetical pricing
  opinions to substitute for observed product use and weaken ScopeProof's evidence discipline.
- Mark Stage 1 complete when paused: rejected because a pause changes no measured count and creates
  no evidence.

## Verification

Implement documentation contracts test-first. Begin with focused failures proving that the
authoritative Stage sections reject a non-zero or missing count, a claimed Stage 2 start, missing
owner authorization, and missing non-outreach language. Then add the packet and roadmap wording.

The final branch must pass:

- Ruff;
- focused readiness-document contracts;
- the complete repository-contract suite;
- the complete test suite with at least 95 percent combined coverage because a test file changes;
- both deterministic benchmarks with zero mismatches and zero must-have False Ready outcomes;
- `git diff --check` and a named-file commit audit; and
- independent read-only review with no unresolved Critical or Important findings.

No package build, installed browser run, release action, or product-runtime change is required for
this docs-and-contracts slice unless an implementation change unexpectedly touches packaged files.

## Boundaries

This work does not start Stage 2, resume Stage 1, contact participants, collect external evidence,
validate a customer or buyer, establish willingness to pay, create pricing, or authorize a product
sale. It does not add accounts, billing, private repositories, hosted source processing,
integrations, generic code review, security scanning, automatic fixes, or paid APIs.

ScopeProof remains an evidence assistant, not a correctness oracle. Users must confirm normalized
acceptance criteria before analysis. Static candidates are not runtime verification. Persisted and
exported product objects remain Pydantic-validated, gates remain deterministic and fail closed,
failed lifecycle operations remain non-mutating, and False Ready remains more harmful than False
Blocked. Reviewer and source-owner identity remain asserted, not authenticated. The GitHub Action
remains opt-in and informational.
