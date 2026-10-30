# Selected-reference context in saved re-review comparisons

## Outcome and authority

The owner requested the next bounded product improvement after PR #226 and delegated routine
design, implementation, automated verification, independent review and checked merge. M1–M3 are
implemented; M3 deliberately excluded selected references from comparisons. This newly authorized
follow-on closes that workflow boundary without describing the original milestone as defective.

A reviewer reopening compatible saved analyses can inspect both sets of attributed selected
references in the workbench and comparison JSON/Markdown, without reloading source or reanalysis.
Usefulness and genuine independent use remain unvalidated; Stage 3 remains dormant.

## Approaches and chosen contract

1. Reuse automatic candidate relocation/modified matching: rejected. Identical text does not
   establish cross-head equivalence, a preserved reviewer assertion, or source continuity.
2. Display only unclassified snapshots: safe but makes exact recorded-context differences harder
   to inspect. Retain both full snapshots and add full-record identity distinctions, chosen below.
3. Add a separate informational comparison: chosen by the implementer under delegated authority.

`scopeproof_core/reviews/selected_reference_comparison.py` provides Pydantic models for a
`SelectedReferenceComparison` containing repository/PR and canonical previous/current lists of
full `ReviewerSelectedReference` values (maximum 32 per side). Reject duplicates and foreign
repository/PR attribution. Retain both owning criteria-source provenance records even for empty
lists, and require each reference to match its own side's full provenance. Across sides compare the
existing source URI/revision/text/digest identity, allowing differing confirmation metadata.
Preserve full raw excerpts, criteria provenance, reviewer, rationale,
timestamps, IDs, exact head, path, line and static E1/E2 type. Compute `record_changes` and
`change_counts` from all serialized reference fields, including asserted attribution and IDs.
Kinds are `identical_record`, `only_previous`, `only_current`. A changed head or metadata produces
separate one-sided records, never a relocation, semantic modification or carried-forward decision.
Reordering inputs does not change canonical output. Ignore serialized derived fields and recompute.

`ReviewComparison.selected_reference_comparison` defaults to `None` for historical comparison
projections that did not include this context. Its existing computed
`reviewer_selected_references_compared` flag reflects availability. New `compare_reviews` output
always includes both lists, including explicit empty lists. A missing section means unavailable,
not proof that no references were recorded. Selected context requires the existing scope snapshots;
validate each side's owning review/head/criteria revision/digest and criterion IDs against them,
and compatible criteria-source identity across all references. Export revalidation catches mutable
tampering and contradictions with the retained inspected inventory/skip/rename facts under existing
M3 source rules. Complete validated input bundles remain the source of new projections.

The workbench renders a separate section with its own record counts and attributed previous/current
references. Markdown and JSON preserve the same distinctions and the non-gating boundary. Historical
projections render an explicit unavailable explanation. Saved-comparison fingerprints and deferred
download leases continue binding the complete saved records, including selected-reference changes.

## Invariants and exclusions

Automatic evidence counts/changes, findings, `criteria_requiring_decision_review`, scope coverage,
gates, decisions, runtime/JUnit context, selected-reference eligibility and record version 6 remain
unchanged. Comparisons remain read-only, detached projections. No historical record rewrite or
migration, new source fetching/retention, matching heuristics, source-authenticity claim, dependency,
adapter, account, release, deployment, outreach, participant review or target-code execution.
All frozen R-002 files, inputs/labels/results/scores and private candidate artifacts stay untouched;
new constructed cases remain separate. No human evidence or accessibility claim is created.

## Finish line

Observe RED→GREEN for recorded-reference visibility, exact full-record identity, cross-head and
attribution changes, empty/legacy projections, ownership/tamper rejection, unchanged gating and
saved bytes, stale selected-only mutations/downloads, and safe rendering. Run full original 95%
coverage, Ruff, lock/diff, unchanged deterministic benchmarks, fresh installed-wheel browser and
Python/Windows compatibility. One independent whole-branch review, supported finding fixes,
exact-head protected CI, guarded merge and resulting-main verification complete this slice.
