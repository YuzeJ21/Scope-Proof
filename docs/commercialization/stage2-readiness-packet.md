# ScopeProof Owner-Led Stage 2 Productization Packet

This packet defines the owner-led productization lane. It is not a customer-validation record,
does not authorize outreach, and does not change the evidence attached to any product claim.

## Current status

- Stage 1: `closed_not_pursued_by_owner`.
- Stage 2: `owner_led_productization_active`.
- 0/5 qualifying reviews.
- 0/3 independent practitioners.
- 0/3 public repositories.
- 0/3 independently observed under-ten-minute completions.
- 0/2 reuse-intent signals.
- Zero participant False Ready observations across zero participant reviews is not a validated
  False Ready rate.

Stage 1 did not pass. The owner chose not to pursue it. Stage 2 begins through explicit owner
authorization without claiming customer validation. This packet does not authorize outreach or
participant contact.

## Owner-led productization scope

Stage 2 may improve:

- product and workflow clarity;
- deterministic evidence quality and fail-closed lifecycle integrity;
- packaging, installation, compatibility, accessibility engineering, and release readiness;
- documentation and public official-source research; and
- separately scoped, non-executing evidence adapters with typed provenance.

Every result remains bounded to its actual evidence. Tests and CI are engineering evidence, not
target-repository runtime proof, accessibility conformance, customer use, demand, or adoption.

This stage does not authorize outreach, participant contact, a merge, release, tag, or package
publication, R-002 retuning, R-003 generation, billing, accounts, private-repository support,
hosted source processing, generic code review, security scanning, automatic fixes, or paid APIs.
Each requires its own owner decision where applicable.

## Optional external discovery

External commercial discovery is optional and separate from owner-led productization. It is not a
Stage 2 entry or exit gate and does not run by default. Outreach, recruitment, participant contact,
or price research requires separate owner authorization.

Passive voluntary feedback may remain available. A response can inform later owner decisions only
when it is attributable to genuine completed use. It does not reopen Stage 1, create stage credit,
or retroactively turn engineering work into customer evidence.

The [30-day design-partner sprint](design-partner-sprint.md) is the optional research protocol. The
[market-positioning hypotheses](market-positioning-hypotheses.md) remain hypotheses until genuine
evidence supports, mixes, or disconfirms them.

## Hypothesis ledger

Every hypothesis starts as `unknown`. Optional external research may later record `supported`,
`mixed`, or `disconfirmed` only with attributable completed-use evidence.

| Hypothesis | Initial state | Evidence source |
|---|---|---|
| Primary user is a product manager, QA practitioner, or engineer | `unknown` | none |
| Likely buyer is in QA, engineering, product operations, or product leadership | `unknown` | none |
| The job is pre-merge acceptance-evidence review at an immutable head | `unknown` | none |
| Attributable gaps or clearer changed-head decisions create recurring value | `unknown` | none |
| A participant independently intends to reuse ScopeProof | `unknown` | none |
| A participant voluntarily agrees to discuss a price hypothesis | `unknown` | none |

USD 99 per team per month and USD 999 per team per year remain research anchors only. They are not
active prices, offers, orders, invoices, purchase agreements, payment requests, or evidence of
willingness to pay.

## Evidence-capture template

This blank template is not product storage and is not a participant record. Use it only after
optional external discovery is separately authorized and genuine completed use exists. Keep an
unavailable answer as `unknown`, a refused answer as `declined`, and an unobserved measurement as
`not observed`.

| Field | Allowed value or evidence requirement | Template value |
|---|---|---|
| Public case and exact reviewed head | Public reference plus 40-character SHA | `unknown` |
| Participant role category | Attributable role category without a direct identifier | `unknown` |
| Completed-review and validated-outcome references | Public references | `unknown` |
| Completion-time evidence | Independent observer category plus public evidence reference | `not observed` |
| Self-reported completion time | Self-reported completion time remains `not observed` | `not observed` |
| Alternative workflow | One of `prefer_different_job`, `existing_alternative_sufficient`, `current_job_and_tool_gap`, `unknown`, or `declined` | `unknown` |
| `outcome` | One of `found_useful_gap`, `showed_only_known_information`, or `created_friction` | `unknown` |
| `useful_gap_category` | One of the seven canonical values below | `unknown` |
| `decision_impact` | One of `changed`, `clarified`, `confirmed_existing`, `no_effect`, or `indeterminate` | `unknown` |
| `friction_category` | One of `installation_or_setup`, `criteria_confirmation`, `evidence_quality`, `runtime_verification`, `decision_or_export`, `comparison_or_rereview`, `other_material_friction`, `none`, `unknown`, or `declined` | `unknown` |
| `evidence_boundary_understanding` | One of `understood`, `misunderstood`, `unsure`, or `declined` | `unknown` |
| `reuse_response` | One of `yes`, `no`, `unsure`, or `declined` | `unknown` |
| `participant_false_ready` | `confirmed`, `not_confirmed`, or `unknown` under the evidence rule below | `unknown` |
| Optional price-discussion response | Yes, no, unsure, or `declined` | `unknown` |
| Evidence source and status | Public reference plus explicit status | `unknown` |

## Canonical decision-value mapping

Persist only the canonical enum value in a future validated qualification record. Decision
predicates evaluate canonical values, never display labels. Reject an unmapped, missing, ambiguous,
or multiply selected value rather than normalizing it heuristically.

| Field | Canonical enum values | Exact public/input mapping |
|---|---|---|
| `outcome` | `found_useful_gap`, `showed_only_known_information`, `created_friction` | `Found a useful previously unknown gap` -> `found_useful_gap`; `Produced only already-known information` -> `showed_only_known_information`; `Created material product friction` -> `created_friction` |
| `useful_gap_category` | `missing_implementation_evidence`, `weak_or_misleading_candidate_evidence`, `missing_test_evidence`, `stale_evidence_after_new_commit`, `unclear_acceptance_criteria`, `another_attributable_public_finding`, `no_new_useful_gap` | `Missing implementation evidence` -> `missing_implementation_evidence`; `Weak or misleading candidate evidence` -> `weak_or_misleading_candidate_evidence`; `Missing test evidence` -> `missing_test_evidence`; `Stale evidence after a new commit` -> `stale_evidence_after_new_commit`; `Unclear acceptance criteria` -> `unclear_acceptance_criteria`; `Another attributable public finding` -> `another_attributable_public_finding`; `No new useful gap` -> `no_new_useful_gap` |
| `decision_impact` | `changed`, `clarified`, `confirmed_existing`, `no_effect`, `indeterminate` | `Changed my review decision` -> `changed`; `Clarified my review decision` -> `clarified`; `Confirmed an existing review decision` -> `confirmed_existing`; `Had no effect on my review decision` -> `no_effect`; `Could not determine a decision` -> `indeterminate` |
| `reuse_response` | `yes`, `no`, `unsure`, `declined` | `Yes, I intend to use ScopeProof on another PR` -> `yes`; `No` -> `no`; `Unsure` -> `unsure`; `Prefer not to answer` -> `declined` |
| `alternative_workflow` | `prefer_different_job`, `existing_alternative_sufficient`, `current_job_and_tool_gap`, `unknown`, `declined` | No current public-form field; require a separate explicit bounded selection |
| `friction_category` | `installation_or_setup`, `criteria_confirmation`, `evidence_quality`, `runtime_verification`, `decision_or_export`, `comparison_or_rereview`, `other_material_friction`, `none`, `unknown`, `declined` | No direct public-form mapping. Free-text friction is non-authoritative context and cannot populate `friction_category`; require a separate explicit bounded selection |
| `evidence_boundary_understanding` | `understood`, `misunderstood`, `unsure`, `declined` | The required checked public evidence-boundary statement maps to `understood`; do not infer any other value without a separate explicit bounded selection |
| `participant_false_ready` | `confirmed`, `not_confirmed`, `unknown` | Derive only through the evidence predicates below; never map a direct form label |

## Optional-discovery decision rules

Optional discovery remains operationally inactive. Separate owner authorization is necessary but
not sufficient to use these rules. Before any qualification record is persisted or any cohort
decision is calculated, implement a Pydantic-validated qualification-record model and an atomic
validated storage boundary with regression coverage. Until that boundary exists, do not persist
records or calculate cohort decisions from this document alone.

No optional-discovery decision may be calculated while the qualifying denominator is zero. If
optional discovery is authorized later, create one canonical qualification record for each
qualifying completed session. The record contains the immutable local `alpha_case_id` and
`review_id`, `qualified_at_utc`, `feedback_issue_number`, and `evidence_snapshot_sha256`, the
SHA-256 digest of the evidence snapshot used at qualification. A mutable public reference does not
qualify; keep any source URL only as non-authoritative context.
`qualified_at_utc` is the UTC commit time of the first successful validated transition from not
qualified to qualified. For an initially incomplete or mismatched submission, use the later atomic
transition that first passes every qualification rule, never the submission, issue-creation, or
draft-record time. Once assigned, `qualified_at_utc` is immutable.
At qualification, derive canonical `outcome` from the validated local outcome record and verify the
public feedback `outcome` matches it exactly after this fixed mapping:
`found_useful_gap` maps to `Found a useful previously unknown gap`,
`showed_only_known_information` maps to `Produced only already-known information`, and
`created_friction` maps to `Created material product friction`. A missing or different public value
keeps the qualification record on hold and is not counted.

Reject a new qualification record before ordering if its `alpha_case_id` or `review_id` already
appears in any qualification record. Order the remaining qualification records by
`(qualified_at_utc, feedback_issue_number) ascending`. Do not assign partial cohort membership.
When at least five eligible unassigned records exist, select the first five in canonical order,
assign positions, and freeze the cohort atomically. Consecutive frozen cohorts occupy positions
1–5, 6–10, and so on. A pre-freeze correction revalidates the record in the unassigned pool; an
invalid record remains on hold and is not eligible for atomic selection. Later edits cannot reorder,
replace, or repartition a frozen cohort.
Corrections annotate the original qualification record and do not create a new cohort member. The
same completed session can appear in at most one cohort. Any post-freeze change to a canonical
qualification or decision field invalidates the affected cohort. Canonical fields are
`alpha_case_id`, `review_id`, `qualified_at_utc`, `feedback_issue_number`,
`evidence_snapshot_sha256`, outcome,
`useful_gap_category`, decision impact, reuse response, alternative workflow, `friction_category`,
evidence-boundary understanding, and `participant_false_ready`. Non-authoritative context or typo
edits outside those fields do not invalidate a cohort. An invalidated cohort remains on hold whether
the correction arrives before or after a decision; do not calculate or recalculate a decision, and
do not allocate the session again. A correction whose revalidated `participant_false_ready`
becomes `confirmed` is exempt from this invalidation hold and returns Stop immediately, even when
`evidence_snapshot_sha256` changes to bind the confirmation. When there are fewer than five unassigned
qualifying records, the next cohort remains on hold and no optional-discovery decision is
calculated.

Useful or decision-relevant is true only when canonical `outcome` is `found_useful_gap` or canonical
`decision_impact` is `changed` or `clarified`. `found_useful_gap` counts only when
`useful_gap_category` is not `no_new_useful_gap`. Any contradiction between `outcome` and
`useful_gap_category` keeps the record on hold and is not counted. `found_useful_gap` is valid only
with one of the six concrete gap-category enums. `showed_only_known_information` is valid only with
`no_new_useful_gap`. `created_friction` is valid only with `no_new_useful_gap`. Every other
`outcome` and `useful_gap_category` pair is contradictory. `confirmed_existing` does not count;
neither do already-known information, friction alone, `no_effect`, `indeterminate`, missing, or
ambiguous responses.

Affirmative repeat use is true only when canonical `reuse_response` is `yes`. Canonical `no`,
`unsure`, `declined`, missing, and ambiguous responses do not count.

All five evidence-boundary understanding values must be `understood` before evaluating any
non-False-Ready Stop predicate, Pivot, Narrow, or Continue. `misunderstood`, `unsure`, `declined`,
missing, and ambiguous values keep the cohort on hold.

Pivot-positive is true only for `prefer_different_job` or `existing_alternative_sufficient`.
`current_job_and_tool_gap`, `unknown`, `declined`, missing, and ambiguous responses do not count
toward Pivot. Pivot requires at least 3 of 5 Pivot-positive records after Stop does not apply.

Confirmed participant False Ready requires all of these conditions: the saved review final gate is
Ready and bound to the exact reviewed head; the participant identifies a specific must-have
criterion that should not have been Ready; the source owner confirms explicit missing or
conflicting acceptance evidence at that head; and `evidence_snapshot_sha256` binds the complete
confirmation record. For a Ready result, missing any other confirmed condition yields `unknown`,
never `not_confirmed`. A final gate that is not Ready is `not_confirmed` under the rule below. A
Ready gate by itself is not a False Ready observation.

`participant_false_ready` is `not_confirmed` only when the exact-head final gate is not Ready, or a
Ready result has both an explicit participant no-False-Ready statement and source-owner
confirmation after checking every must-have criterion. `evidence_snapshot_sha256` binds that
negative confirmation. Otherwise classify `unknown`.

Continue requires all 5 of 5 `participant_false_ready` values to be `not_confirmed`. A `confirmed`
value triggers Stop; `unknown` keeps the cohort on hold.

Narrow-positive friction category is one of `installation_or_setup`, `criteria_confirmation`,
`evidence_quality`, `runtime_verification`, `decision_or_export`, `comparison_or_rereview`, or
`other_material_friction`. `none`, `unknown`, and `declined` do not count toward Narrow. Narrow
requires the same Narrow-positive `friction_category` in at least 3 of 5 complete records.
`Created material product friction` requires one Narrow-positive `friction_category`; `none` is
contradictory and keeps the record on hold. `unknown` and `declined` remain incomplete under the
completeness rule.

Evaluate confirmed participant False Ready before the completeness precondition. Any `confirmed`
record returns Stop immediately even when other cohort records are incomplete, `unknown`, or
`declined`. If no record is `confirmed`, before applying the remaining Stop predicates, Pivot,
Narrow, or Continue, all five records must have complete bounded decision inputs for outcome,
`useful_gap_category`, decision impact, reuse response, alternative workflow, `friction_category`,
evidence-boundary understanding, `participant_false_ready`, and `evidence_snapshot_sha256`. Any
missing, ambiguous, `unknown`, or `declined` required decision input keeps the cohort on hold; do
not evaluate Stop or any lower-precedence decision.

Precedence, highest first: Stop, Pivot, Narrow, Continue.

1. **Stop** for any confirmed False Ready, fewer than 2 of 5 useful or decision-relevant sessions,
   or zero explicit affirmative repeat-use responses.
2. **Pivot** when Stop does not apply and at least 3 of 5 records are Pivot-positive.
3. **Narrow** when neither higher rule applies and the same Narrow-positive `friction_category`
   occurs in at least 3 of 5 complete records.
4. **Continue discovery** only when none of the higher rules applies, at least 2 of 5 sessions are
   useful or decision-relevant, all 5 of 5 members explicitly understood the evidence boundary,
   and all 5 of 5 `participant_false_ready` values are `not_confirmed`.

These optional-discovery rules do not control owner-led productization. Missing evidence defaults
to hold for discovery and cannot be interpreted as support.

## Boundaries

Do not infer any signal from silence. `Unknown`, `declined`, `not observed`, incomplete, ambiguous,
and negative outcomes remain visible.

This packet does not reopen Stage 1 and does not establish customer validation, a validated user or
buyer, demand, adoption, repeat use, commercial value, willingness to pay, or validated pricing.
It authorizes no external contact, recruitment issue, announcement, recurring monitor, private
data collection, form automation, database, account, billing, checkout, subscription, private-
repository support, hosted processing, integration, generic code review, scanner, automatic fix,
release, tag, or package publication.
