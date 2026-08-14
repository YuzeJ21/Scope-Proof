# ScopeProof Stage 2 Readiness Packet

This packet prepares dormant post-use research materials. It does not activate Stage 2, authorize
outreach, or create product-validation or commercial evidence.

## Current status

Measured product-validation state: `waiting_for_inbound_public_alpha_submission`.

Owner operating posture: Stage 1 is paused. Stage 2 readiness materials only; Stage 2 has not
begun. This preparation does not authorize outreach.

- 0/5 qualifying reviews.
- 0/3 independent practitioners.
- 0/3 public repositories.
- 0/3 independently observed under-ten-minute completions.
- 0/2 reuse-intent signals.
- Zero participant False Ready observations across zero participant reviews is not a validated
  False Ready rate.

## Activation gate

Every Stage 1 exit condition must have genuine evidence before Stage 2 can be considered. Stage 2
also requires separate owner authorization after those conditions pass. Prepared materials, tests,
demos, releases, downloads, issue activity, owner rehearsals, and elapsed time earn no stage credit.

## Post-use discovery guide

These questions remain dormant until a participant completes a qualifying public Stage 1 review,
selects an outcome, and the record is validated at the exact reviewed head. Ask them in order:

1. What workflow would you otherwise have used for this pull-request decision?
2. What attributable result, if any, did ScopeProof expose?
3. Did the result change, clarify, confirm, or have no effect on a decision?
4. Which workflow step created the most material friction?
5. Was the distinction between candidate evidence, runtime verification, and correctness clear?
6. Would you independently bring another public pull request through this workflow?
7. After this completed use, would you voluntarily discuss the research-only team-price
   hypothesis?

Do not ask for names, email addresses, employers, private repositories, confidential requirements,
customer data, payment data, purchase authorization, or sales-contact permission. A participant
may answer `declined`, and no positive or negative meaning may be inferred from that choice.

The [30-day design-partner sprint](design-partner-sprint.md) remains the canonical future research
workflow and stop-gate source. The
[market-positioning hypotheses](market-positioning-hypotheses.md) remain hypotheses until genuine
completed use supports, mixes, or disconfirms them.

## Hypothesis ledger

Every hypothesis starts as `unknown`. The only allowed later states are `supported`, `mixed`, and
`disconfirmed`, and each change requires attributable completed-use evidence.

| Hypothesis | Initial state | Evidence source |
|---|---|---|
| Primary user is a product manager, QA practitioner, or engineer | `unknown` | none |
| Likely buyer is in QA, engineering, product operations, or product leadership | `unknown` | none |
| The job is pre-merge acceptance-evidence review at an immutable head | `unknown` | none |
| Manual checklists, spreadsheets, lifecycle suites, test management, or code review are insufficient alternatives | `unknown` | none |
| Attributable gaps or clearer changed-head decisions create recurring value | `unknown` | none |
| Setup, criteria confirmation, public-only scope, unresolved output, or workflow cost is the dominant adoption risk | `unknown` | none |
| A participant independently intends to reuse ScopeProof | `unknown` | none |
| A participant voluntarily agrees to discuss the price hypothesis after use | `unknown` | none |

USD 99 per team per month and USD 999 per team per year are research anchors only. They are not
active prices, offers, orders, invoices, purchase agreements, or payment requests.

## Evidence-capture template

This blank Markdown template is not connected to product storage and is not a participant record.
Do not fill it before genuine completed use. Keep an unavailable answer as `unknown`, a refused
answer as `declined`, and a measurement that did not occur as `not observed`.

| Field | Allowed value or evidence requirement | Template value |
|---|---|---|
| Public case and exact reviewed head | Public case reference plus 40-character SHA | `unknown` |
| Participant role category | Product, QA, engineering, or another attributable role category | `unknown` |
| Source-owner confirmation | Public authority path for the confirmed criteria | `unknown` |
| Completed review and outcome | Saved-review and validated-outcome references | `unknown` |
| Completion-time band | Under five minutes, five to ten, over ten, or `not observed` | `not observed` |
| Alternative workflow | Participant's explicit post-use response | `unknown` |
| Attributable result | Useful gap, already-known information, friction, or no new information | `unknown` |
| Decision impact | Changed, clarified, confirmed, no effect, or could not determine | `unknown` |
| Largest friction | Source, criteria, coverage, decision, export, integration, or another attributable category | `unknown` |
| Evidence-boundary understanding | Understood, misunderstood, unsure, or `declined` | `unknown` |
| Reuse response | Yes, no, unsure, or `declined` | `unknown` |
| Optional price-discussion response | Yes, no, unsure, or `declined` | `unknown` |
| Evidence source and status | Public reference plus `unknown`, `declined`, or `not observed` when applicable | `unknown` |

## Decision rules

- **Continue** only while completed genuine use exposes attributable value, reviewers understand
  the evidence boundary, and confirmed False Ready remains zero.
- **Narrow** when one observed workflow stage repeatedly creates most material friction.
- **Pivot** when participants consistently prefer a different job or existing alternatives are
  sufficient.
- **Stop** when fewer than two of five completed reviews are useful or decision-relevant, nobody
  intends repeat use, or confirmed False Ready cannot remain zero.

No decision may be calculated while the qualifying denominator is zero. Activity metrics,
prepared documents, owner opinions, silence, and elapsed time cannot supply a denominator or a
signal.

## Boundaries

Do not infer any signal from silence. `Unknown`, `declined`, `not observed`, incomplete, ambiguous,
and negative outcomes remain visible and are never rewritten as support.

This packet does not resume Stage 1, activate Stage 2, authorize outreach, contact or recruit a
participant, open a recruitment issue, post an announcement, start a recurring monitor, collect
external evidence, or establish a customer, buyer, demand, adoption, repeat use, commercial value,
or pricing evidence.

It adds no form, database, account, billing, checkout, subscription, private-repository support,
hosted source processing, integration, generic code review, security scanner, automatic fix, paid
API, release, tag, or package publication. A separate owner decision cannot replace the genuine
evidence required by the activation gate.
