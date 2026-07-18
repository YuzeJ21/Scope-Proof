# Concierge public-alpha host checklist

This is the repository owner's operational index for one supervised ScopeProof trial. It does not
replace the linked participant instructions or create validation evidence. Use public information
only. Never retain credentials, private source, customer data, or confidential requirements.

## Stage status reference

| Status | Use only when |
| --- | --- |
| `not_started` | No qualification decision exists. |
| `qualified` | Every public-PR qualification condition is explicit. |
| `criteria_confirmed` | The source owner confirmed the normalized atomic criteria before analysis. |
| `review_completed` | ScopeProof completed the deterministic review for the recorded head SHA. |
| `outcome_received` | The participant selected and recorded exactly one bounded outcome. |
| `declined` | The case was out of scope or the recipient declined. |
| `withdrawn` | The participant stopped after initially agreeing. |

Do not fill this repository file with a person or case. Persist only a qualified case through the
existing Pydantic-validated `scopeproof alpha` commands after the required confirmations.

If repeated maintenance goals end at `waiting_for_inbound_public_alpha_submission`, use the
[participant evidence unblocker](participant-evidence-unblocker.md) instead of starting another
overnight monitor.

Submit a public alpha case through the inbound-only issue form:
https://github.com/YuzeJ21/Scope-Proof/issues/new?template=public-alpha-case.yml

The [30-day Design Partner Sprint](../commercialization/design-partner-sprint.md) defines the
commercial-research evidence and stop gates. It does not authorize outreach or create evidence.

## Host sequence

- [ ] Install and verify the current release using the [README quickstart](../../README.md#quickstart).
- [ ] Wait for an inbound public-alpha case submission. Do not manually contact participants or
      store outreach records in the repository.
- [ ] Apply every [public-PR qualification check](public-pr-qualification-checklist.md).
- [ ] Normalize criteria with the [acceptance-criteria confirmation template](acceptance-criteria-confirmation-template.md), then return them to the source owner for confirmation before analysis.
- [ ] Follow the [ten-minute participant quickstart](participant-quickstart.md), including `scopeproof alpha init` before the review.
- [ ] Conduct the review under the [confirmed dogfood protocol](../dogfood/public-pr-protocol.md). Do not execute the PR or convert static evidence into runtime verification.
- [ ] Let the participant accept, reject, or mark findings ambiguous; do not choose for them.
- [ ] Ask the participant to select exactly one value from the [public-alpha outcome form](outcome-form.md).
- [ ] Only after the local outcome is complete, offer the voluntary public feedback form:
      https://github.com/YuzeJ21/Scope-Proof/issues/new?template=public-alpha-feedback.yml
      Do not select timing, decision impact, reuse intent, or design-partner interest for the
      participant.
- [ ] Record report and quotation consent independently. Both remain off unless explicitly granted.
- [ ] Use a public summary only when the validated case has report consent. Never publish local notes or infer quotation consent.

## Stop and route rules

- Stop on private source, confidential material, missing criteria authority, decline, or withdrawal.
- A public PR without source-owner-confirmed criteria may be a technical smoke only.
- Installation, replies, and technical smokes do not close the roadmap's external validation gate.
- Preserve incomplete and negative outcomes without rewriting them as successes.
