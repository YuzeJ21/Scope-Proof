# Candidate-selection completeness disclosure

## Goal and reproduced gap

The owner requested the next concrete automatic product improvement after PR #213, without
personal testing or qualifying reviews. At main `7086cd1`, twelve constructed lines that pass the
existing lexical filters produce eight candidates. Diagnostics report twelve overlapping lines,
zero below threshold and eight accepted candidates, but omit the explicit eligible count and cap.

Show when the candidate list is bounded, without improving or retuning candidate matching. This
is constructed engineering evidence, not proof of relevance, correctness, independent use or demand.

## Selected approach and alternatives

- Increase the cap or change retrieval: excluded; that changes candidate behavior and requires
  separately authorized holdout evaluation. Frozen R-002 remains untouched and no R-003 is generated.
- Infer historical omissions from existing counters: rejected; overlap includes rejected lines,
  so historical eligibility cannot be reconstructed reliably.
- Record actual selection metadata for new analyses and disclose unknown historical state:
  selected under the owner's execution authorization.

## Data and validation

Add three optional fields to `CriterionRetrievalDiagnostic`:

- `eligible_candidate_count`: number of matches after existing lexical/identifier/threshold filters.
- `candidate_limit`: the existing eight-candidate selection limit.
- `omitted_candidate_count`: eligible count minus selected (`accepted_candidate_count`) count.

All three are `None` for historical diagnostics. Otherwise all three must be present as strict
integers (not booleans, floats or numeric strings); eligible/omitted counts are nonnegative and
limit is positive. Validate eligible <= inspectable lines, selected <= min(eligible, limit),
and omitted == eligible - selected. Keep existing bundle-level evidence/count validation.

Populate the fields from the existing passing-match list and selected output. Centralize the
unchanged limit of eight without changing filters, scores, type diversity, ordering, IDs, excerpts,
citations or evidence levels. This adds metadata, not a new gate input or evidence item.

## Presentation and compatibility

A UI-independent presentation helper returns:

> 8 of 12 candidates passing search filters shown; 4 omitted during selection (limit: 8).

Eligible counts include matching input entries. The existing selector also suppresses identical
duplicates, so selected count may be below min(eligible, limit). Do not attribute every omission
solely to the cap or change existing deduplication to satisfy a metadata invariant.

For historical diagnostics it returns:

> Candidate selection completeness was not recorded for this review.

Use the shared text in the workbench, Markdown and HTML, beside the existing non-evidence boundary.
JSON and the CSV `retrieval_diagnostic` cell carry the same facts as validated typed fields,
including explicit nulls for unknown historical values. Do not add another CSV column or persist
presentation prose. This is format-appropriate disclosure, not a new report format.

Saved-record versions need no bump: the optional additive fields preserve older records without
inventing counts. Test raw historical payloads through real storage/export boundaries. Existing
gate results, criteria confirmation, reviewer decisions and PR #213 CSV context stay unchanged.
This guarantees older-record readability in the updated source, not forward compatibility with
older executables that reject unfamiliar diagnostic fields.

## Completion evidence

Observe behavioral RED/GREEN for boundary counts, excluded overlapping lines, mixed evidence,
schema contradictions, historical unknowns, all report formats, saved-review CLI and workbench.
Compare canonical evidence bytes with the pre-change constructed baseline. Extend the existing
installed-wheel journey with a preseeded constructed capped review and real CSV/JSON downloads.
Run the full suite with the unchanged unrounded 95% floor, lint, benchmarks and existing hosted
package/compatibility checks. Obtain independent agent review, merge only after exact-head checks,
then verify main. No release, deployment, outreach or Stage 3 advancement is authorized.
