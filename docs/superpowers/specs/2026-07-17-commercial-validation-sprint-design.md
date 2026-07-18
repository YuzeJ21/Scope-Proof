# ScopeProof Commercial Validation Sprint Design

## Decision

Turn the existing genuine public-alpha path into a bounded commercial-discovery path without
building billing, private-repository access, accounts, outreach automation, or an unvalidated paid
product.

The sprint must answer one question: after reviewing a genuine public PR, do independent
practitioners experience enough acceptance-coverage value to use ScopeProof again and discuss a
team product?

## Current truth

- ScopeProof v0.2.0 is released and the reviewer-first engineering reset is complete.
- The product supports reviewer-confirmed criteria for public GitHub pull requests.
- No qualifying external completed alpha case, repeat-use behavior, or willingness-to-pay evidence
  exists yet.
- The public site already routes inbound candidates to the public-alpha case issue form.
- The owner path remains passive: no email, direct messaging, scraping, contact list, automated
  outreach, or notification-only GitHub activity.
- The evaluation-only use policy remains unchanged.

## Considered approaches

### 1. Build Local Pro immediately

Add private local Git ingestion, commercial licensing, and a price before external validation.
This could create a sellable package sooner, but it would spend engineering effort before proving
that acceptance coverage produces repeat value. Reject this approach for the current sprint.

### 2. Publish pricing and add billing immediately

Expose a checkout or paid plan while the product is public-repository-only. This would test payment
directly, but it requires a billing decision and creates a promise the current product is not ready
to fulfill. Reject this approach.

### 3. Extend the genuine-alpha path into commercial discovery

Keep the existing free inbound flow, collect bounded value and reuse signals after a real review,
and define explicit evidence gates for any later Local Pro decision. Choose this approach because
it tests the highest-risk assumption without changing product safety, licensing, or cost.

## Scope

### Public design-partner sprint guide

Create one canonical owner-facing guide under `docs/commercialization/`. It defines the 30-day
queue, qualifying case, value signals, price-test wording, evidence thresholds, and stop rules. It
must distinguish a pricing hypothesis from an offer and must not ask the owner to contact people.

### Participant-facing feedback intake

Extend the existing public-alpha feedback issue form after a participant completes a genuine
review. Collect only bounded public signals:

- the genuine public PR;
- the related alpha-case issue;
- the reviewed head SHA;
- a completion-time bucket;
- the participant-selected outcome;
- the useful-gap category, if any;
- whether the review changed or clarified a decision;
- whether the participant would use ScopeProof on another PR;
- whether the participant would voluntarily discuss a design-partner product at the stated price
  hypothesis.

The form must not collect a name, email address, LinkedIn profile, employer, payment information,
private repository, confidential material, or a binding purchase commitment. A submitted issue is
participant-authored evidence; an empty form, draft, or owner-authored example is not validation.

### Public positioning

Update the public site and README to describe the free design-partner review as an optional path
for qualified public PRs. The public copy must say:

- the review is free;
- no paid product or billing is active;
- the participant must own or be authorized to confirm the criteria;
- the result may be useful, already known, incomplete, or friction;
- a pricing question is research, not a purchase requirement;
- likes, stars, downloads, and submissions without completed outcomes do not count.

### Roadmap gate

Add a commercial-discovery gate after genuine public alpha and before any Local Pro build decision.
Proceed only when the existing alpha gates pass and at least two independent completed
participants both intend to reuse ScopeProof and voluntarily agree to discuss the team-price
hypothesis. Do not describe those discussions as revenue, orders, or willingness to pay.

## Price hypothesis

Test two equivalent anchors only after a participant completes a review:

- USD 99 per team per month; or
- USD 999 per team per year.

These are research anchors, not active prices. The repository must not add checkout links, payment
processors, invoices, license keys, or billing code in this sprint.

## Evidence semantics

The following do not count as commercial evidence:

- a constructed demo;
- an owner-authored or synthetic case;
- a release download, star, view, impression, or form visit;
- a case submission without a completed reviewed outcome;
- a hypothetical price opinion collected before the participant experiences the product;
- any statement inferred from silence.

A reusable commercial signal requires a completed genuine review tied to a public PR, public
requirements, source-owner-confirmed criteria, an exact head SHA, a participant-selected outcome,
and explicit voluntary reuse or design-partner intent.

## Safety and privacy

- Do not execute pull-request code.
- Do not use paid OpenAI, LLM, or other model APIs.
- Do not add billing, private repositories, accounts, organizations, or fork testing.
- Do not send email, direct messages, automated outreach, or GitHub progress comments.
- Do not persist credentials or contact information.
- Do not invent participants, outcomes, pricing interest, or validation.
- Keep consent off unless the participant explicitly supplies it through the existing workflow.
- Preserve `.coverage 2` unchanged.

## Testing

Repository contract tests must require:

- the canonical commercial sprint guide and links from README and the public site;
- the exact price hypotheses and the statement that they are not active prices;
- bounded completion-time, reuse-intent, and design-partner-interest fields in the feedback form;
- the absence of contact, payment, private-repository, and binding-purchase fields;
- roadmap gates that prevent Local Pro work before genuine alpha and commercial signals;
- unchanged public-alpha qualification, evidence, consent, and False Ready boundaries;
- no public claim that a participant, customer, paid plan, or revenue exists.

Run the focused repository contracts first, then Ruff, the deterministic benchmark, the complete
test suite with the existing coverage floor, documentation-link checks, and desktop plus 390 px
public-site verification.

## Deferred work

The following remain explicitly deferred until the evidence gate passes and the owner makes a
separate product decision:

- local private-repository ingestion;
- a commercial license or EULA;
- hosted source processing;
- accounts, teams, permissions, or shared storage;
- payment processing or billing;
- Jira, Linear, or other source integrations;
- SSO, audit-log, self-hosting, SLA, or enterprise procurement features.

## Completion condition

This implementation is complete when the public intake, guide, positioning, roadmap, and contract
tests are synchronized and verified. The commercial-validation milestone remains open until real
participants complete the required reviews and explicitly supply the required signals.
