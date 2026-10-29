# Actionable CSV review handoff

## Intent and observed gap

The owner requested a concrete automatic product improvement beyond status checks, without
personal testing or qualifying reviews. At main `a963205`, a constructed review with all four
criteria explicitly accepted still requires final acceptance. The validated gate records
`final_acceptance_required`, but CSV contains only `Review incomplete` and the accepted decisions.
Its recipient loses the review-level reason and recovery instruction already present in Markdown.

This slice makes spreadsheet handoffs actionable. It supplies engineering evidence only and
does not establish demand, independent use, runtime correctness, accessibility conformance or beta
readiness. It does not advance Stage 3 or authorize publication.

## Approaches and selected design

- Change retrieval: rejected for this slice; the frozen research record requires separate holdout
  evaluation, and the owner has not authorized R-003 generation.
- Add a new handoff format or collaboration service: unnecessary for the reproduced gap.
- Extend the existing CSV with validated gate context: selected by the agent under the owner's
  execution authorization. The shared exporter already serves CLI and workbench downloads.

Append these columns, preserving all existing columns and their order:

| Column | Source |
| --- | --- |
| `gate_reason_codes` | `GateDecision.reason_codes` |
| `gate_blocking_criteria` | `GateDecision.blocking_criteria` |
| `gate_conditional_criteria` | `GateDecision.conditional_criteria` |
| `gate_unresolved_criteria` | `GateDecision.unresolved_criteria` |
| `gate_resolved_exceptions` | `GateDecision.resolved_exceptions` |
| `gate_guidance` | Existing deterministic `gate_guidance()` output |

Every new cell is a JSON array, including empty arrays. Preserve the validated model's ordering,
UTF-8 text and exact identifiers; use existing CSV quoting/formula-safety conventions. Repeat the
review-level context on every criterion row, so a filtered or separately shared row retains it.
Keep one row per criterion; a zero-criterion input retains the existing header-only behavior.

## Boundaries and verification

All data comes through the existing Pydantic export validation and deterministic gate preflight.
Do not change gate evaluation, criteria confirmation, attribution, final acceptance, evidence
retrieval, saved schemas, source identity, historical results or frozen research inputs. Preserve
existing scalar formula neutralization and reversible JSON list cells. Unknown or invalid bundles
continue to fail closed at the existing boundary; this is an export projection, not new evidence.

First reproduce missing final-acceptance guidance with literal regression expectations. Cover
mixed gate groups, accepted exceptions, failing CI, deterministic bytes, row identity and unchanged
reviewer decisions. Exercise saved-review CLI CSV output and real installed-wheel CSV downloads.
Run repository checks, the full suite with the existing unrounded 95% floor, benchmarks, package
and compatibility lanes. Obtain independent agent review, merge only with exact-head checks, and
verify resulting main. All actors/cases are constructed automation, not qualifying human reviews.
