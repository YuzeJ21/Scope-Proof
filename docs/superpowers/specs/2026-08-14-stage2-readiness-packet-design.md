# Owner-Led Stage 2 Productization Design

## Context

ScopeProof has a substantial engineering foundation but no external product-validation evidence.
The recorded Stage 1 measurements are 0/5 qualifying reviews, 0/3 independent practitioners, 0/3
public repositories, 0/3 independently observed under-ten-minute completions, and 0/2 reuse-intent
signals. Zero False Ready observations across zero participant reviews is not a validated False
Ready rate.

On 2026-08-14, the owner chose not to pursue the external Stage 1 program and authorized an
owner-led Stage 2 productization strategy. This is a strategy decision, not evidence that Stage 1
passed and not customer validation. The product may advance through owner-directed engineering and
product work while external commercial discovery remains optional.

## Decision

Use two explicit stage statuses:

- Stage 1: `closed_not_pursued_by_owner`.
- Stage 2: `owner_led_productization_active`.

Stage 1 closes with every historical measurement still at zero. Closing the program satisfies none
of its former targets and creates no participant, customer, adoption, demand, usability, timing,
reuse, pricing, or willingness-to-pay evidence.

Stage 2 begins by explicit owner authorization. It is an owner-led productization lane, not a
commercial-validation stage. Engineering work may improve the existing public-repository product,
but every claim remains limited to the evidence actually produced.

## Stage 2 scope

Owner-led Stage 2 may include:

- product and workflow clarity;
- deterministic evidence quality and fail-closed lifecycle integrity;
- packaging, installation, compatibility, accessibility engineering, and release readiness;
- documentation and public official-source market research; and
- separately scoped, non-executing evidence adapters that preserve typed provenance.

This authorization does not include a release, tag, package publication, merge, outreach,
participant contact, R-002 retuning, R-003 generation, billing, accounts, private-repository
support, hosted source processing, generic code review, security scanning, automatic fixes, or
paid APIs. Each remains separately owner-gated where applicable.

## Optional external discovery lane

External product or commercial discovery is optional and separate from Stage 2 productization. It
does not run by default and requires a separate owner decision before outreach or participant
contact. Passive voluntary feedback may remain available, but it is not required for owner-led
productization and cannot retroactively turn engineering work into customer evidence.

If optional discovery is later used, each response must remain attributable to genuine completed
use. Missing, declined, ambiguous, private, self-reported timing, and zero-denominator states remain
visible and fail closed. Pricing anchors remain research hypotheses only; no response is a price,
offer, order, customer, willingness-to-pay result, or purchase commitment.

## Stage 3 and Stage 4

Stage 3 remains a separate owner decision for a release candidate or bounded beta. It requires the
engineering and evidence gates defined for that future slice, but it must not claim customer
validation merely because Stage 2 productization occurred.

Stage 4 remains a separate owner decision for narrow expansion. Optional external evidence may
inform it if genuine evidence exists, but absent external evidence is recorded as absent rather
than replaced with owner opinion or engineering activity.

## Documentation architecture

The current-facing stage model lives in:

- `ROADMAP.md`;
- `docs/releases/v0.2.3-status-and-next-stages.md`; and
- `docs/commercialization/stage2-readiness-packet.md`, retitled and rewritten as the owner-led
  Stage 2 productization packet.

Public README, site, alpha-feedback, outcome, quickstart, checklist, design-partner, market-
positioning, and changelog surfaces must use the same boundary. Historical audits and research
artifacts keep their dated statements; current documents must not cite them as the active stage
status.

## Repository contracts

Section-scoped contracts must require:

- Stage 1 status `closed_not_pursued_by_owner` in both authoritative stage sections;
- all five Stage 1 measurements at zero and the zero-denominator False Ready limitation;
- explicit wording that Stage 1 was not passed, waived, or validated;
- Stage 2 status `owner_led_productization_active` and explicit owner authorization;
- an enumerated owner-led scope and separately gated actions;
- external commercial discovery described as optional, separate, and non-validating;
- public feedback described as optional and without a pricing field; and
- negative guards against customer validation, validated demand, validated price, willingness to
  pay, Stage 1 completion/pass, and claims that engineering evidence substitutes for customers.

The contract must inspect authoritative sections independently so a stale status cannot be masked
by correct wording elsewhere.

## Alternatives considered

1. **Close Stage 1 and activate owner-led Stage 2 — selected.** This records the owner's actual
   strategy without fabricating validation and keeps external discovery available but optional.
2. **Waive or mark Stage 1 complete — rejected.** “Waived” or “complete” could be misread as a
   passed gate and would erase the zero-evidence truth.
3. **Renumber every stage — rejected.** Renumbering creates needless historical churn and makes
   earlier audits harder to interpret.
4. **Keep Stage 2 dormant — rejected by the owner.** It would preserve a dependency on external
   input the owner has explicitly chosen not to pursue.

## Verification

Revise the repository contracts first and observe their expected failure against the old stage
model. Then update the smallest coherent set of current-facing documents. Run the focused contract,
all repository contracts, Ruff, the complete suite with at least 95 percent combined coverage, both
deterministic benchmarks, and `git diff --check`. Obtain independent read-only review and resolve
every actionable Critical or Important finding before pushing the final reviewed head.

PR #195 remains unmerged until the revised exact head is independently reviewed, current,
mergeable, and every available check is terminal and green or truthfully classified.

## Product boundaries

ScopeProof remains an evidence assistant, not a correctness oracle. Users confirm normalized
acceptance criteria before analysis. ScopeProof never executes target-repository code. Static
candidates are not runtime verification. Persisted and exported objects remain Pydantic-validated.
Gate behavior remains deterministic and fail closed; failed lifecycle commands remain non-mutating;
False Ready remains more harmful than False Blocked. Reviewer and source-owner identity remain
asserted, not authenticated. The GitHub Action remains opt-in and informational.
