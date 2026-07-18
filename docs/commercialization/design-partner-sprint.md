# ScopeProof 30-day Design Partner Sprint

ScopeProof is testing whether independent reviewers get enough value from deterministic
acceptance coverage to use it again and voluntarily discuss a possible team product. The current
design-partner review is free, public-repository-only research. No paid product or billing is
active.

The current external state is `waiting_for_external_participant_evidence`. This guide makes the
next genuine case actionable; it does not create participant evidence by itself.

## Current state

ScopeProof v0.2.0 can turn source-owner-confirmed acceptance criteria and one genuine public
GitHub pull request into an inspectable requirement-to-evidence review. It does not execute the
pull request, invent requirements, replace QA, or prove correctness.

No qualifying completed participant case, repeat-use behavior, customer, revenue, validated
price, or paid demand is currently claimed.

## Qualifying case

A case enters the sprint only when all of these are explicit and public:

- a genuine public GitHub pull-request URL;
- a public HTTPS requirements source;
- authority from the source owner or a directly authorized criteria confirmer;
- confirmation that no private code, customer data, credentials, private links, or confidential
  requirements are included;
- one confirmed criterion per independently judgeable behavior;
- a participant who will inspect the result and select their own outcome.

Submit the candidate through the
[inbound public-alpha case form](https://github.com/YuzeJ21/Scope-Proof/issues/new?template=public-alpha-case.yml).
A submission is only an intake candidate. It is not validation until a genuine review and a
participant-selected outcome are complete.

## Ordered 30-day queue

1. Accept only inbound cases that pass every public qualification requirement.
2. Let the participant confirm the normalized criteria before analysis.
3. Run the standard public PR → confirm criteria → review coverage → record decisions → export
   workflow without executing repository code.
4. Bind the saved review to the exact head SHA and participant-selected outcome.
5. Record timing, useful-gap category, decision impact, and friction after the review.
6. Ask about reuse only after the participant has inspected the completed result.
7. Offer the optional research-only price question only after genuine product use.
8. Preserve negative, incomplete, ambiguous, and no-new-information outcomes without rewriting
   them as success.
9. Evaluate the evidence gates after five completed reviews; do not substitute elapsed time or
   repository activity.

The owner path stays passive. Do not send email or direct messages, scrape profiles, build a
contact list, automate outreach, or add notification-only GitHub comments.

## Signals recorded only after a completed review

Record the participant's explicit selection for:

- completion time: under five minutes, five to ten minutes, more than ten minutes, or no
  inspectable report;
- outcome: useful gap, already-known information, incomplete review, or product friction;
- useful-gap category: missing implementation, weak or misleading evidence, missing test
  evidence, stale evidence after a new commit, unclear criteria, another attributable public
  finding, or no new useful gap;
- decision impact: changed, clarified, confirmed an existing decision, had no effect, or could not
  be determined;
- reuse intent: yes, no, unsure, or prefer not to answer;
- optional design-partner discussion: yes, no, unsure, or prefer not to answer.

Do not infer any signal from silence. The public feedback form must not collect names, email
addresses, LinkedIn profiles, employers, payment information, sales-contact permission, private
repositories, customer information, or confidential material.

## Research-only price hypotheses

The two anchors are **USD 99 per team per month** and **USD 999 per team per year**. They are
research hypotheses only, not active prices or an offer for sale.

Discuss them only after a genuine participant completes a review. A response is voluntary, may be
declined, and is not a purchase agreement, order, payment authorization, invoice request, or
permission for sales contact. This sprint adds no checkout, subscription, billing, payment
processor, commercial license, or license key.

## Evidence that does not count

The following do not establish product or commercial validation:

- stars;
- views or impressions;
- downloads;
- issue submissions without completed reviews;
- constructed demos;
- synthetic cases;
- owner-authored examples;
- technical smokes, CI results, or release activity;
- a pricing opinion collected before product use;
- an owner-authored or inferred outcome.

## Continue, narrow, pivot, and stop gates

Continue the public sprint while genuine participants find attributable gaps, understand the
candidate-versus-decision boundary, and supply repeat-use intent without confirmed False Ready.

Narrow the workflow if criteria confirmation or another single stage repeatedly consumes most of
the session. Prioritize the observed stage instead of adding broad integrations.

Pivot the positioning if reviewers consistently prefer a different job than acceptance coverage
or cannot act on the resulting matrix.

Stop rather than manufacture momentum if fewer than two of five completed sessions reveal a
useful or decision-relevant result, nobody intends to bring another PR, or confirmed False Ready
cannot remain zero.

## Local Pro decision gate

Local Pro remains deferred. Consider a separate product decision only after every genuine-alpha
gate in the public roadmap passes and:

- at least two independent completed participants explicitly intend to use ScopeProof on another
  PR;
- at least two independent completed participants voluntarily agree to discuss the team-price
  hypothesis;
- the useful result affects review before approval, review after a new commit, or an
  acceptance/release decision;
- zero confirmed False Ready outcomes remain;
- every misleading candidate and material friction point remains recorded.

These signals are research evidence. They are not revenue, orders, customers, paid demand, or
willingness to pay.

## Deferred capabilities

Until the evidence gate passes and the owner makes a separate decision, do not build:

- local private-repository ingestion;
- a commercial license or EULA;
- billing, payment processing, checkout, invoices, subscriptions, or license keys;
- hosted source processing;
- accounts, teams, permissions, or shared storage;
- Jira, Linear, or other requirements integrations;
- SSO, audit logs, self-hosting, SLAs, or enterprise procurement features.

## Current waiting condition

Remain at `waiting_for_external_participant_evidence` until a non-owner participant supplies all
qualifying public inputs, completes the review at an exact head SHA, and selects the honest
outcome. Do not poll, send outreach, or create a synthetic substitute while waiting.
