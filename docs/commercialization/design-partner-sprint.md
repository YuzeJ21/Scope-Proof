# ScopeProof 30-day Design Partner Sprint

If Stage 2 is activated, ScopeProof will test whether independent reviewers get enough value from
deterministic acceptance coverage to use it again and voluntarily discuss a possible team product.
Any future design-partner review is free, public-repository-only research. No paid product or
billing is active.

The current external state is `waiting_for_inbound_public_alpha_submission`. This guide is dormant
Stage 2 preparation; it does not create participant evidence or make a Stage 1 case actionable for
discovery by itself.

## Current state

ScopeProof v0.2.3 can turn source-owner-confirmed acceptance criteria and one genuine public
GitHub pull request into an inspectable requirement-to-evidence review. It does not execute the
pull request, invent requirements, replace QA, or prove correctness.

No qualifying completed participant case, repeat-use behavior, customer, revenue, validated
price, or paid demand is currently claimed.

## Stage 2 activation gate

Every Stage 1 exit target genuinely passes and the owner separately authorizes Stage 2 before this
guide may be used. Until both conditions hold, every discovery or price question remains dormant;
one genuine use, a completed review, prepared material, engineering work, or elapsed time is
insufficient. This gate does not authorize outreach.

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

After the Stage 2 activation gate passes, use this queue for qualifying public cases only. Before
activation, no discovery, reuse, or price question may be asked.

1. Accept only inbound cases that pass every public qualification requirement.
2. Let the participant confirm the normalized criteria before analysis.
3. Run the standard public PR → confirm criteria → review coverage → record decisions → export
   workflow without executing repository code.
4. Bind the saved review to the exact head SHA and participant-selected outcome.
5. Record independently observed timing only when an independent observer category and a specific
   public evidence reference support it; otherwise record timing as `not observed`. Record the
   useful-gap category, decision impact, and friction after the review.
6. Ask about reuse only after the participant has inspected the completed result.
7. Offer the optional research-only price question only after the Stage 2 activation gate has
   passed and genuine product use is complete.
8. Preserve negative, incomplete, ambiguous, and no-new-information outcomes without rewriting
   them as success.
9. Evaluate the evidence gates after five completed reviews; do not substitute elapsed time or
   repository activity.

The owner path stays passive. Do not send email or direct messages, scrape profiles, build a
contact list, automate outreach, or add notification-only GitHub comments.

## Signals recorded only after a completed review

Record the participant's explicit selection for the non-timing fields below; record timing only
with independent provenance:

- completion time: under five minutes, five to ten minutes, or more than ten minutes, only when an
  independent observer category and specific public evidence reference support it; otherwise
  record `not observed`, and never credit self-reported time toward the Stage 1 under-ten-minute
  target;
- outcome: useful gap, already-known information, or product friction;
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

Discuss them only after every Stage 1 exit target genuinely passes, the owner separately authorizes
Stage 2, and after a genuine participant completes a review; genuine product use alone is
insufficient. A response is voluntary, may be declined, and is not a purchase agreement, order,
payment authorization, invoice request, or permission for sales contact. This sprint adds no
checkout, subscription, billing, payment processor, commercial license, or license key.

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

After activation, apply the deterministic [Stage 2 readiness packet decision
rules](stage2-readiness-packet.md#decision-rules). This guide does not independently calculate a
Continue, Narrow, Pivot, or Stop outcome. Missing, ambiguous, private, or inadequately proven
evidence remains fail-closed and cannot justify continuation, scope change, or outreach.

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

Remain at `waiting_for_inbound_public_alpha_submission` until a non-owner participant supplies all
qualifying public inputs, completes the review at an exact head SHA, and selects the honest
outcome. Do not poll, send outreach, or create a synthetic substitute while waiting; no discovery,
reuse, or price questions may be asked.
