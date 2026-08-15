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
| Completion-time evidence | Independent observer category, distinct-observer relationship, and public evidence reference | `not observed` |
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
| `timing_evidence` | `not_observed`, `observed_under_5m`, `observed_5_to_10m`, `observed_over_10m` | `Not independently observed` -> `not_observed`; `Independently observed: under 5 minutes` -> `observed_under_5m`; `Independently observed: 5 to 10 minutes` -> `observed_5_to_10m`; `Independently observed: more than 10 minutes` -> `observed_over_10m` |
| `timing_observer_category` | `not_observed`, `source_owner`, `authorized_criteria_representative`, `independent_observer` | `Not independently observed` -> `not_observed`; `Source owner` -> `source_owner`; `Directly authorized criteria representative` -> `authorized_criteria_representative`; `Independent observer` -> `independent_observer` |
| `timing_observer_relationship` | `not_observed`, `distinct_from_participant` | `Not independently observed` -> `not_observed`; `Observer was not the participant` -> `distinct_from_participant` |
| `useful_gap_category` | `missing_implementation_evidence`, `weak_or_misleading_candidate_evidence`, `missing_test_evidence`, `stale_evidence_after_new_commit`, `unclear_acceptance_criteria`, `another_attributable_public_finding`, `no_new_useful_gap` | `Missing implementation evidence` -> `missing_implementation_evidence`; `Weak or misleading candidate evidence` -> `weak_or_misleading_candidate_evidence`; `Missing test evidence` -> `missing_test_evidence`; `Stale evidence after a new commit` -> `stale_evidence_after_new_commit`; `Unclear acceptance criteria` -> `unclear_acceptance_criteria`; `Another attributable public finding` -> `another_attributable_public_finding`; `No new useful gap` -> `no_new_useful_gap` |
| `decision_impact` | `changed`, `clarified`, `confirmed_existing`, `no_effect`, `indeterminate` | `Changed my review decision` -> `changed`; `Clarified my review decision` -> `clarified`; `Confirmed an existing review decision` -> `confirmed_existing`; `Had no effect on my review decision` -> `no_effect`; `Could not determine a decision` -> `indeterminate` |
| `reuse_response` | `yes`, `no`, `unsure`, `declined` | `Yes, I intend to use ScopeProof on another PR` -> `yes`; `No` -> `no`; `Unsure` -> `unsure`; `Prefer not to answer` -> `declined` |
| `alternative_workflow` | `prefer_different_job`, `existing_alternative_sufficient`, `current_job_and_tool_gap`, `unknown`, `declined` | No current public-form field; require a separate explicit bounded selection |
| `friction_category` | `installation_or_setup`, `criteria_confirmation`, `evidence_quality`, `runtime_verification`, `decision_or_export`, `comparison_or_rereview`, `other_material_friction`, `none`, `unknown`, `declined` | No direct public-form mapping. Free-text friction is non-authoritative context and cannot populate `friction_category`; require a separate explicit bounded selection |
| `evidence_boundary_understanding` | `understood`, `misunderstood`, `unsure`, `declined` | `I understand ScopeProof is an evidence assistant, not a correctness oracle; static or implementation evidence does not prove test or runtime verification.` -> `understood`; do not infer any other value without a separate explicit bounded selection |
| `participant_false_ready_attestation` | `affirmed_specific_must_have_should_not_be_ready`, `affirmed_no_false_ready_after_complete_must_have_check`, `not_applicable_final_gate_not_ready` | No current public-form field; require a separate exact bounded selection and never derive it from prose |
| `source_owner_false_ready_attestation` | `confirmed_missing_or_conflicting_acceptance_evidence`, `confirmed_no_missing_or_conflicting_evidence_after_complete_must_have_check`, `not_applicable_final_gate_not_ready` | No current public-form field; require a separate exact bounded selection and never derive it from prose |
| `participant_false_ready` | `confirmed`, `not_confirmed`, `unknown` | Derive only through the evidence predicates below; never map a direct form label |

## Optional-discovery decision rules

Optional discovery remains operationally inactive. Separate owner authorization is necessary but
not sufficient to use these rules. Before any qualification record is persisted or any cohort
decision is calculated, implement a Pydantic-validated qualification-record model and an atomic
validated storage boundary with regression coverage. That work must first extend the
Pydantic-validated local `AlphaCaseRecord` to persist `alpha_case_issue_url` during case
initialization. Legacy records without that identity remain ineligible. Do not infer or backfill the
association. Until that boundary exists, do not persist records or calculate cohort decisions from
this document alone; do not enable feedback matching.

No optional-discovery decision may be calculated while the qualifying denominator is zero. If
optional discovery is authorized later, create one canonical qualification record for each
qualifying completed session. The record contains the immutable local `alpha_case_id` and
`review_id`, `public_pr_url`, `reviewed_head_sha`, `requirements_source_url`,
`alpha_case_issue_url`, `qualified_at_utc`, `feedback_issue_number`, and
`evidence_snapshot_sha256`, the SHA-256 digest of the evidence snapshot used at qualification. A
mutable public reference does not qualify; keep any other source URL only as non-authoritative
context.

The separately authorized runtime boundary must define a Pydantic model named
`OptionalDiscoveryEvidenceSnapshotV1` with `extra="forbid"`. It contains exactly these fields and no
others: `schema_version` fixed to `optional-discovery-evidence-snapshot-v1`, `alpha_case_id`,
`review_id`, `public_pr_url`, `reviewed_head_sha`, `requirements_source_url`,
`alpha_case_issue_url`, `qualified_at_utc`, `feedback_issue_number`, `outcome`,
`final_gate`, `confirmed_criteria_sha256`, `source_owner_confirmed`,
`checked_must_have_criterion_ids`, `participant_false_ready_attestation`,
`participant_false_ready_criterion_id`, `source_owner_false_ready_attestation`,
`timing_evidence`, `timing_observer_category`, `timing_observer_relationship`,
`timing_public_evidence_url`,
`timing_public_evidence_content_sha256`,
`useful_gap_category`, `decision_impact`, `reuse_response`, `alternative_workflow`,
`friction_category`, `evidence_boundary_understanding`, and `participant_false_ready`.
`evidence_snapshot_sha256` is not part of the snapshot payload and cannot hash itself. Validate the
snapshot first, then calculate `canonical_bytes` exactly as
`json.dumps(snapshot.model_dump(mode="json"), sort_keys=True, separators=(",", ":"),
ensure_ascii=False, allow_nan=False).encode("utf-8")`; persist
`sha256(canonical_bytes).hexdigest()`. Any writer using different fields, schema version, ordering,
whitespace, Unicode escaping, non-finite numbers, or encoding is non-conforming and the record
remains on hold.

The V1 model uses `ConfigDict(extra="forbid", strict=True, frozen=True)`. Every field is required;
the model has no aliases and no defaults. Its exact strict field types and JSON representations are:

- `schema_version` is `Literal["optional-discovery-evidence-snapshot-v1"]`.
- `alpha_case_id` is `StrictStr` matching `^alpha-[0-9a-f]{32}$`; `review_id` is `StrictStr`
  matching `^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$`.
- `public_pr_url`, `alpha_case_issue_url`, `requirements_source_url`, and
  `timing_public_evidence_url` are `StrictStr` with length 1 through 2,048. URLs remain `StrictStr`
  rather than a coercing or normalizing URL type.
  A field validator requires `public_pr_url` to match the canonical public GitHub pull-request
  pattern. `alpha_case_issue_url` must be the exact canonical public GitHub issue URL
  `https://github.com/YuzeJ21/Scope-Proof/issues/{positive_integer}` in the configured intake
  repository `YuzeJ21/Scope-Proof`. The reviewed PR may belong to a different public repository.
  The two evidence-source URLs must pass the shared canonical public-HTTPS-source validator without
  changing the input string, and the timing field's exact `Not observed` sentinel is permitted only
  for the not-observed path. The validated exact string is serialized; redirects or URL
  normalization cannot silently change it.
- `reviewed_head_sha` is `StrictStr` matching `^[0-9a-f]{40}$`.
  `confirmed_criteria_sha256` and `timing_public_evidence_content_sha256` are `StrictStr` matching
  `^[0-9a-f]{64}$`.
- `feedback_issue_number` is `StrictInt` from 1 through 2,147,483,647; Boolean values are rejected.
- `qualified_at_utc` is `StrictStr` in exactly `YYYY-MM-DDTHH:MM:SS.ffffffZ`. A field validator
  parses it as a real UTC instant and requires formatting that instant back to the same string, so
  offsets, omitted or variable fractional seconds, and impossible dates are rejected.
- `final_gate` is `Literal["ready", "conditional", "blocked", "needs_review"]`.
  `source_owner_confirmed` is `StrictBool` constrained to `true`.
- `checked_must_have_criterion_ids` is a tuple of `StrictStr` values, with zero through 256 unique
  items in exact criterion order; every item has length 1 through 128 and matches
  `^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$`. It serializes as one JSON array in tuple order.
- `participant_false_ready_attestation` and `source_owner_false_ready_attestation` use the exact
  canonical `Literal` sets in their mapping-table rows.
  `participant_false_ready_criterion_id` is `StrictStr | None`; its string branch uses the same
  criterion-ID constraints and its absent branch serializes only as JSON `null`.
- The enum-backed fields are `Literal` values from the canonical decision-value mapping, with no
  aliases: `outcome`, `timing_evidence`, `timing_observer_category`,
  `timing_observer_relationship`, `useful_gap_category`,
  `decision_impact`, `reuse_response`, `alternative_workflow`, `friction_category`,
  `evidence_boundary_understanding`, and `participant_false_ready`. Each field's `Literal` members
  are exactly the canonical enum values in its mapping-table row.

No Boolean, integer, datetime, URL, enum, list, or string coercion is allowed. JSON strings are the
exact validated strings, integers are JSON numbers, the Boolean is JSON `true`, the tuple is one
JSON array, and `None` is JSON `null`. These types plus the canonical dump recipe are the complete
V1 byte contract; a future type, bound, pattern, normalization, or serialization change requires a
new schema version.

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
Observed timing requires a non-`not_observed` `timing_observer_category`,
`timing_observer_relationship` `distinct_from_participant`, and a valid public HTTPS
`timing_public_evidence_url` that passes the same canonical public-source validation and is publicly
reachable. Not independently observed requires `timing_observer_category` `not_observed`,
`timing_observer_relationship` `not_observed`, and `timing_public_evidence_url` exactly
`Not observed`. Never infer observer distinctness from an observer category: a source owner or
criteria representative who is also the participant cannot qualify as an independent observer.
Every other timing-provenance combination remains on hold and is not counted; no provenance field
can upgrade a `not_observed` timing selection.
For observed timing, `timing_public_evidence_url` must be a canonical public GitHub issue URL. Fetch
it only with `GET https://api.github.com/repos/{owner}/{repository}/issues/{number}`, an
unauthenticated request that must never send a token. Send exactly
`Accept: application/vnd.github+json` and `X-GitHub-Api-Version: 2022-11-28`; use a five-second
timeout, redirects disabled, no retries or pagination, and a 256 KiB response-byte cap. Require a
200 JSON object, require response `html_url` exactly equals `timing_public_evidence_url`, and reject
a missing, null, empty, or over-65,536-code-point body.

Validate a frozen `TimingPublicEvidenceV1` model with
`ConfigDict(extra="forbid", strict=True, frozen=True)`. It contains exactly
`schema_version`, `source_url`, `github_issue_node_id`, and `body`: `schema_version` is
`Literal["timing-public-evidence-v1"]`; `source_url` is the exact validated canonical issue URL;
`github_issue_node_id` is `StrictStr` matching `^[A-Za-z0-9_=-]{1,128}$` and equals the response
`node_id`; and `body` is `StrictStr` with length 1 through 65,536 and equals the response body
without trimming or normalization. Serialize this projection with the same sorted-key, compact,
non-ASCII-escaping, finite-only canonical JSON recipe used above. The
`timing_public_evidence_content_sha256` is the 64-character lowercase SHA-256 of those canonical
projection bytes. Hash the canonical projection bytes, never raw HTTP response bytes, decoded HTML,
headers, transfer encoding, or redirect output. A mutable URL without this content digest does not
qualify.

For observed timing, the exact `body` must itself be the canonical JSON serialization of a strict,
frozen `TimingEvidenceAttestationV1` with `extra="forbid"`. It contains exactly
`schema_version`, `alpha_case_id`, `review_id`, `public_pr_url`, `reviewed_head_sha`,
`timing_evidence`, `timing_observer_category`, `timing_observer_relationship`,
`observer_attestation`, and `source_owner_attestation`. `schema_version` is
`Literal["timing-evidence-attestation-v1"]`; the identity, PR, and head fields use the exact V1
snapshot types; `timing_evidence` is one of the three observed timing Literals;
`timing_observer_category` is one of the three non-`not_observed` category Literals;
`timing_observer_relationship` is `Literal["distinct_from_participant"]`;
`observer_attestation` is
`Literal["observed_this_exact_session_and_selected_band_is_accurate"]`; and
`source_owner_attestation` is
`Literal["confirmed_observer_and_timing_for_this_exact_session"]`.

Every attestation identity and timing field must exactly match the validated local alpha case,
saved review, and feedback selection. Parse with strict validation, serialize with the same
canonical JSON recipe, and require that canonical reserialization must equal the issue body
byte-for-byte as UTF-8 with no trailing newline. Arbitrary prose, extra fields, a different session,
head, observer relationship, or time band keeps the record on hold. The attestations are asserted,
not authenticated, and cannot establish product correctness or customer validation. A later
revalidation whose canonical projection digest changes invalidates the record. For not-observed
timing, the field remains the SHA-256 of the exact UTF-8 bytes `Not observed` and no timing
attestation issue is used.
The feedback issue's `alpha_case_id`, `review_id`, `public_pr_url`, `reviewed_head_sha`,
`requirements_source_url`, and `alpha_case_issue_url` must exactly match the validated local alpha
case and saved review. For the case issue, the complete URL must exactly match the validated local
alpha case; a numeric issue match alone never qualifies. Any identity, head, PR, source, or
case-issue mismatch keeps the qualification record on hold and is not counted.

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
`alpha_case_id`, `review_id`, `public_pr_url`, `reviewed_head_sha`, `requirements_source_url`,
`alpha_case_issue_url`, `qualified_at_utc`, `feedback_issue_number`,
`evidence_snapshot_sha256`, outcome, timing evidence, timing observer category, timing observer
relationship, timing public evidence URL,
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
Ready and bound to the exact reviewed head; `participant_false_ready_attestation` is exactly
`affirmed_specific_must_have_should_not_be_ready`; the participant identifies one specific checked
must-have criterion; `source_owner_false_ready_attestation` is exactly
`confirmed_missing_or_conflicting_acceptance_evidence`; and `evidence_snapshot_sha256` binds the
complete confirmation record. For a Ready result, missing any other confirmed condition yields
`unknown`, never `not_confirmed`, but this missing-condition rule applies only after the affirmative
participant attestation. A Ready negative attestation is evaluated only by the `not_confirmed` rule
below and is not a missing confirmed condition. A final gate that is not Ready is `not_confirmed`
under the rule below. A Ready gate by itself is not a False Ready observation.

For every False Ready classification, the snapshot binds `final_gate`,
`confirmed_criteria_sha256`, `source_owner_confirmed`, `checked_must_have_criterion_ids`,
`participant_false_ready_attestation`, `participant_false_ready_criterion_id`, and
`source_owner_false_ready_attestation`. `confirmed_criteria_sha256` must equal the validated digest
of the exact ordered confirmed-criterion snapshot. `source_owner_confirmed` must be `true`.
`checked_must_have_criterion_ids` must equal the complete ordered must-have set from that snapshot.
For `confirmed`, use the exact affirmative participant/source-owner attestations above and require
the criterion ID to name one checked must-have criterion. For a Ready `not_confirmed` result, the
participant attestation is exactly `affirmed_no_false_ready_after_complete_must_have_check`, the
criterion ID is `null`, and the source-owner attestation is exactly
`confirmed_no_missing_or_conflicting_evidence_after_complete_must_have_check`. For a non-Ready final
gate, both attestations are exactly `not_applicable_final_gate_not_ready` and the criterion ID is
`null`. Any missing, mismatched, or contradictory attestation yields `unknown`.

No semantic interpretation of prose may affect `participant_false_ready`. Free-text notes are
non-authoritative context, are excluded from the snapshot payload, and cannot populate or override
either attestation enum, the criterion ID, or the derived classification.

`participant_false_ready` is `not_confirmed` only when the exact-head final gate is not Ready, or a
Ready result has both exact negative participant/source-owner attestations after checking every
must-have criterion. `evidence_snapshot_sha256` binds that negative confirmation. Otherwise
classify `unknown`.

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
