# PR #195 Timing and Cohort Integrity Repair Design

## Context

PR #195 activates owner-led Stage 2 productization while keeping external discovery optional and
non-validating. Exact-head review found two fail-closed integrity gaps in that optional lane:

- the public feedback form can record a completion-time band while separately declaring that the
  time was not independently observed; and
- the optional-discovery packet does not define how more than five qualifying sessions are ordered
  and assigned to non-overlapping cohorts.

These gaps do not change the owner-led productization authorization, but they must be repaired
before merge because optional evidence must remain internally consistent and reproducible.

## Decision

Make the timing classification and cohort allocation deterministic without adding outreach,
participant automation, storage, or commercial functionality.

### Timing evidence

Replace the independent completion-time and observation-status dropdowns with one authoritative
required dropdown whose mutually exclusive values combine both facts:

- Not independently observed;
- Independently observed: under 5 minutes;
- Independently observed: 5 to 10 minutes; and
- Independently observed: more than 10 minutes.

Replace free-text timing support with three required structured timing-provenance fields: one
required `timing_observer_category` dropdown, one required `timing_observer_relationship`
dropdown, and one required `timing_public_evidence_url` input. The
observer dropdown has only `Not independently observed`, `Source owner`, `Directly authorized
criteria representative`, and `Independent observer`. Observed timing is usable only with a
non-not-observed observer category, relationship `distinct_from_participant`, and a validated,
publicly reachable HTTPS evidence URL. A not-observed timing selection requires not-observed values
for both category and relationship plus the exact `Not observed` sentinel in the URL field. An
observer category never proves distinctness. Every other combination remains on hold. Observed
timing also requires `timing_public_evidence_content_sha256`, the digest of the exact fetched public
evidence content. The authoritative packet's bounded, unauthenticated GitHub Issue API fetch must
project the exact canonical issue URL, stable node ID, and unnormalized body into the strict
`TimingPublicEvidenceV1` canonical JSON payload before hashing. Raw HTTP bytes, HTML wrappers,
headers, redirects, and transfer encoding are never hashed; a mutable URL without the canonical
projection digest does not qualify.

### Cohort allocation

Each optional-discovery session receives a canonical qualification record containing:

- the immutable local `alpha_case_id` and `review_id`;
- the public feedback issue number;
- the UTC timestamp when the session first satisfied every qualification rule; and
- an `evidence_snapshot_sha256` field containing the SHA-256 digest of the evidence snapshot used
  for qualification.

Before hashing, separately authorized implementation must validate the exact versioned Pydantic
payload `OptionalDiscoveryEvidenceSnapshotV1` with `extra="forbid"`. Its field set and
`schema_version` are exactly those declared in the authoritative packet; the digest field is
excluded. Canonical bytes use sorted-key, compact, non-ASCII-escaping, finite-only JSON encoded as
UTF-8, exactly as the packet specifies, and the persisted digest is
`sha256(canonical_bytes).hexdigest()`.

The model must use `ConfigDict(extra="forbid", strict=True, frozen=True)` and the authoritative
packet's strict field types and exact JSON representations. Every field is required with no aliases
or defaults. IDs, hashes, timestamps, URLs, statements, and the nullable criterion ID use the
packet's exact `StrictStr` bounds and patterns; issue numbers use bounded `StrictInt`; source-owner
confirmation uses constrained `StrictBool`; checked must-have IDs use the bounded ordered tuple;
and every decision field uses the exact canonical `Literal` set. No coercion or URL/datetime
normalization may change the validated input or canonical bytes. Changing any type, bound, pattern,
normalization, or representation requires a new snapshot schema version.

The snapshot also binds `final_gate`, `confirmed_criteria_sha256`, `source_owner_confirmed`, the
complete ordered `checked_must_have_criterion_ids`, `participant_false_ready_attestation`,
`participant_false_ready_criterion_id`, and `source_owner_false_ready_attestation`. The two
attestation fields use only the packet's exact canonical `Literal` values; semantic prose is
non-authoritative and excluded from the snapshot. These are the validated inputs for
`participant_false_ready`; the derived enum alone is insufficient. A Ready negative attestation
follows only the packet's complete exact-enum `not_confirmed` predicate; its intentionally null
criterion ID is not treated as a missing affirmative-confirmation condition.

`qualified_at_utc` is the UTC commit time of the first successful validated transition from not
qualified to qualified. An initially incomplete or mismatched submission uses the later atomic
transition that first passes every qualification rule, never the submission, issue-creation, or
draft-record time. Once assigned, `qualified_at_utc` is immutable.

Any future qualification boundary must derive canonical `outcome` from the validated local outcome
record and verify that the public feedback `outcome` matches it exactly. The fixed mapping is
`found_useful_gap` maps to `Found a useful previously unknown gap`,
`showed_only_known_information` maps to `Produced only already-known information`, and
`created_friction` maps to `Created material product friction`. A missing or different public value
keeps the record on hold and is not counted.

Every other decision field follows the packet's exact canonical enum and public-label mapping.
Decision predicates evaluate canonical values, never display labels, and free-text friction cannot
populate `friction_category`.

At qualification, every identity, head, PR, source, and case-issue field must match exactly between
the feedback issue and the validated local alpha case and saved review. The explicit
evidence-boundary attestation maps to `understood`; a generic completed-review eligibility checkbox
does not. Before feedback matching can be enabled, separately authorized implementation must extend
the Pydantic-validated local `AlphaCaseRecord` to persist the full canonical
`alpha_case_issue_url` during case
initialization. Legacy records without it remain ineligible; do not infer or backfill the
association. The issue URL must belong to the configured `YuzeJ21/Scope-Proof` intake repository;
the reviewed PR may belong to another public repository. The complete URL—not only its issue
number—must match between the feedback issue and local alpha case.

Reject a new qualification record before ordering if its `alpha_case_id` or `review_id` already
appears in any qualification record. This makes the existing one-session-only rule enforceable even
when duplicate public feedback issues are submitted.

Order qualifying sessions by `(qualified_at_utc, feedback_issue_number)` ascending. Do not assign
partial cohort membership. When five eligible unassigned records exist, select the first five in
canonical order, assign positions, and freeze the cohort atomically. A pre-freeze correction
revalidates the record in the unassigned pool; an invalid record remains on hold and is not eligible
for selection. Later edits cannot reorder, replace, or repartition a frozen cohort. Corrections
annotate the original qualification record and never create another cohort member. Any post-freeze
change to a canonical qualification or decision field invalidates the affected cohort and keeps it
on hold. A correction whose revalidated
`participant_false_ready` becomes `confirmed` is exempt from this invalidation hold and returns
Stop immediately, preserving the highest-precedence False Ready rule. Until five unassigned
qualifying records exist, the next cohort remains on hold and no optional-discovery decision is
calculated.

`Created material product friction` requires one Narrow-positive `friction_category`; `none` is
contradictory and keeps the record on hold. This prevents a complete-looking friction outcome from
reaching Continue without a bounded material-friction category.

## Alternatives considered

1. **Static contract repair — selected.** Update the form, packet, and repository contracts. This
   fixes the reviewed boundaries without creating a new ingestion service or product feature.
2. **Build a runtime discovery ledger and validator.** This could enforce the rules in software but
   would expand PR #195 beyond documentation and strategy readiness.
3. **Resolve the findings without changes.** Rejected because contradictory timing and competing
   cohort partitions would violate deterministic, fail-closed evidence handling.

## Test-first verification

Add focused repository-contract assertions before changing either authoritative surface. The
timing regression must fail while provenance is free text and must require the combined timing
dropdown plus the two structured, fail-closed provenance fields. The cohort regression must fail
while ordering and freezing are unspecified and must require the canonical tuple, consecutive
five-record batching, immutable freeze, correction handling, and incomplete-cohort hold.

After the focused red-green cycles, run all repository contracts, Ruff, the complete suite with at
least 95 percent combined coverage, both deterministic benchmarks, YAML parsing, and
`git diff --check`. Push the exact repair head, resolve only the repaired review threads, and wait
for exact-head review and hosted checks before merging PR #195.

## Boundaries

This repair creates no Stage 1 credit, customer validation, demand, adoption, timing result, reuse
signal, price evidence, or outreach authorization. Stage 1 remains
`closed_not_pursued_by_owner`; owner-led Stage 2 productization remains
`owner_led_productization_active`. ScopeProof remains an evidence assistant, never executes target-
repository code, and treats False Ready as more harmful than False Blocked.
