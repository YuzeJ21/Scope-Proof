# ScopeProof Concierge Alpha Sprint Design

## Context

ScopeProof already has an installable `v0.1.23` release, a public site, a participant quickstart,
validated local alpha-case records, a LinkedIn launch draft, an inbound qualification message, and
an evidence-gated roadmap. The current implementation has 769 passing tests, one skipped live test,
and 97 percent measured line coverage.

Those assets make a public-alpha trial possible. They have not produced the two remaining Stage 1
facts: a genuine public pull request reviewed against source-owner-confirmed criteria and the
participant's recorded outcome. Additional releases, synthetic cases, monitors, and broad product
features cannot supply those facts.

The chosen activation strategy is LinkedIn direct message first. The current playbook primarily
describes publishing a public post and responding after a volunteer contacts the owner. It does not
give the owner a bounded outbound sequence, and its public site links to LinkedIn's generic home
page rather than a useful eligibility action. The participant instructions are accurate but split
across installation, qualification, quickstart, dogfood, and outcome documents.

## Objective

Make one manually recruited, supervised ScopeProof trial easier to start and complete without
automating outreach, weakening evidence rules, or representing recruitment activity as product
validation.

The sprint is complete when the repository contains and verifies the improved activation path. The
public-alpha Stage 1 gate remains open until an external participant supplies genuine evidence.

## Approaches considered

### Concierge activation — selected

Prepare a small manual outreach sequence, a single host checklist, and a useful public-site
eligibility action. This is the shortest path to observing real participant friction and requires
no new service or paid dependency. Its limitation is that the owner must select contacts and send
messages personally.

### Self-service onboarding expansion

Add new CLI automation or a hosted intake flow before recruitment. This could help later but would
encode assumptions about friction that no participant has demonstrated. It also increases product
and privacy surface before the alpha gate is satisfied.

### Broad public campaign

Publish widely and optimize impressions. This is operationally simple but poorly targeted. Views,
likes, stars, and unqualified replies are not ScopeProof validation and cannot justify product
changes.

## Product boundaries

- Public GitHub pull requests and public HTTPS requirement sources only.
- The participant must own or be explicitly authorized to confirm the normalized criteria.
- Every message is selected, personalized, and sent manually by the repository owner.
- No email, message automation, profile scraping, contact harvesting, recurring follow-up,
  notification workflow, paid API, LLM API, billing, form backend, analytics, or database.
- No participant name, LinkedIn profile, direct-message transcript, or contact list is committed to
  the repository.
- No private code, confidential requirement, credential, customer data, or secret is requested or
  retained.
- ScopeProof does not execute pull-request code or present static implementation candidates as test
  or runtime verification.
- Recruitment, interest, installation, and technical smokes are funnel events, not product
  validation.
- Report publication and quotation permission remain separate, explicit, and off by default.

## Activation flow

```text
Owner selects a relevant practitioner
  -> owner sends one personalized LinkedIn DM
  -> recipient voluntarily replies with public case information
  -> owner applies every qualification check
  -> source owner confirms normalized criteria
  -> owner hosts the ten-minute local review
  -> participant selects one bounded outcome
  -> ScopeProof stores the validated local outcome and consent state
```

An unclear, unsuitable, confidential, or withdrawn case stops without being converted into alpha
evidence. A public PR without criteria authority may be routed only to a clearly labeled technical
smoke.

## Repository changes

### DM-first outreach sequence

Extend `docs/launch/linkedin-alpha-playbook.md` with a `DM-first outreach` section before the
existing inbound response instructions. It contains:

- one warm-contact template for a known PM, QA practitioner, or engineer;
- one cold-contact template that explains why that specific person's public work appears relevant;
- one optional follow-up, sent manually no sooner than seven days after the first message;
- a stop rule: no further message after no response to the follow-up or after any decline;
- a personalization checklist requiring the owner to verify the person's role and the public work
  referenced rather than inserting fabricated familiarity;
- an explicit request not to send private or confidential material.

The templates ask first whether the recipient has a genuine public PR whose criteria they own or
are authorized to confirm. They do not ask the recipient to install ScopeProof in the first message
and do not claim customers, accuracy, adoption, or prior external validation.

### Concierge host checklist

Add `docs/alpha/concierge-host-checklist.md` as the owner's single operational index. It links to,
rather than duplicates, authoritative instructions for:

1. release installation and checksum verification;
2. public-PR qualification;
3. criteria normalization and confirmation;
4. alpha-case initialization;
5. deterministic review and evidence inspection;
6. participant decision and outcome recording;
7. consent-gated public-summary handling.

The checklist distinguishes owner actions from participant decisions. It includes a stage-status
table with `not_started`, `qualified`, `criteria_confirmed`, `review_completed`,
`outcome_received`, `declined`, and `withdrawn`. The table is an empty reusable template and never
contains a fabricated participant row.

### Public-site eligibility action

Replace the generic `https://www.linkedin.com/` secondary button in `site/index.html`. The button
will link to the checked-in public-PR qualification checklist and read `Check whether your PR
qualifies`. Supporting copy continues to say that the owner recruits and replies through LinkedIn
DM, but the public site will not pretend that a generic LinkedIn homepage opens a conversation with
the owner.

The primary alpha action remains the ten-minute participant quickstart. No personal LinkedIn URL is
invented or committed.

### Navigation

Link the concierge host checklist from the launch playbook and the roadmap's Stage 1 activation
paragraph. Do not add it to participant-facing instructions as a required participant document;
it is an owner operations aid.

## Validation and regression coverage

Extend `tests/test_repository_contracts.py` with focused contracts that verify:

- warm, cold, follow-up, seven-day, decline, confidentiality, and manual-send boundaries exist in
  the launch playbook;
- the host checklist links to every authoritative step and contains all allowed stage values;
- the host checklist contains no populated participant record or contact-data field;
- the public site contains the qualification action and no generic LinkedIn destination;
- the roadmap and launch playbook link to the host checklist;
- the new copy does not claim validation, customers, runtime correctness, or automatic outreach.

Run Ruff, the focused repository-contract tests, the full test suite with coverage, the
deterministic benchmark, and `git diff --check`. Existing Pydantic alpha models remain the only
persisted outcome contract; this sprint introduces no new storage object.

## Operating targets and interpretation

The owner may use the playbook to contact five to ten carefully selected practitioners. This is an
operating target, not a product metric or repository completion condition.

- No replies means the targeting or opening message may need revision.
- Replies without qualified cases indicate an eligibility or audience mismatch.
- Qualified cases that stop before review identify onboarding friction.
- Completed reviews without outcomes identify outcome-capture friction.
- Exactly one participant-selected outcome is evidence for that case only.

The repository must not claim a conversion rate, adoption, usefulness, or beta readiness from the
number of messages sent. Negative, declined, withdrawn, and incomplete cases remain visible in the
owner's manual operations without being rewritten as successes.

## Completion and external handoff

After the repository changes pass review and merge, the owner performs the human-only steps:

1. identify five to ten relevant practitioners without scraping;
2. personalize and manually send the approved DM;
3. stop messaging on decline or after the single unanswered follow-up;
4. return a qualified public PR and source-owner confirmation to the supervised workflow;
5. record the participant's exact outcome and consent choices.

Codex can prepare and maintain the repository assets, validate public URLs supplied by a
participant, run the supervised ScopeProof workflow on an authorized public case, and record the
Pydantic-validated outcome. Codex cannot invent contacts, send messages automatically, infer
authority or consent, or declare the external gate complete without a real participant.
