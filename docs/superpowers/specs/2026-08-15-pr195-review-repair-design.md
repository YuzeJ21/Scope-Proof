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

Replace the two required observer-detail inputs with one optional supporting-details field. An
observed selection is usable only when the field includes both an observer category and a specific
public evidence reference. Missing, ambiguous, private, or malformed support fails closed to
`not observed`. A support field cannot upgrade a `Not independently observed` selection.

### Cohort allocation

Each optional-discovery session receives a canonical qualification record containing:

- the public feedback issue number;
- the UTC timestamp when the session first satisfied every qualification rule; and
- a digest or immutable reference for the evidence snapshot used for qualification.

Order qualifying sessions by `(qualified_at_utc, feedback_issue_number)` ascending. Allocate the
ordered stream once into consecutive cohorts of five: positions 1–5, 6–10, and so on. Freeze a
cohort when its fifth member is assigned. Later edits cannot reorder, replace, or repartition a
frozen cohort. Corrections annotate the original qualification record and never create another
cohort member. Any post-freeze change to a canonical qualification or decision field invalidates
the affected cohort and keeps it on hold. Until five unassigned qualifying records exist, the next
cohort remains on hold and no optional-discovery decision is calculated.

## Alternatives considered

1. **Static contract repair — selected.** Update the form, packet, and repository contracts. This
   fixes the reviewed boundaries without creating a new ingestion service or product feature.
2. **Build a runtime discovery ledger and validator.** This could enforce the rules in software but
   would expand PR #195 beyond documentation and strategy readiness.
3. **Resolve the findings without changes.** Rejected because contradictory timing and competing
   cohort partitions would violate deterministic, fail-closed evidence handling.

## Test-first verification

Add focused repository-contract assertions before changing either authoritative surface. The
timing regression must fail while independent time-band and observation-status fields remain and
must require the combined dropdown plus fail-closed support rule. The cohort regression must fail
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
