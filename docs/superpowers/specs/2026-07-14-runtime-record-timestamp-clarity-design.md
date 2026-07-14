# Runtime Record Timestamp Clarity Design

## Problem

`RuntimeEvidence` persists an immutable timestamp for every manually supplied runtime
observation. The local workbench now renders the other persisted review fields, but omits this
timestamp. A reviewer therefore cannot distinguish when otherwise similar observations were
recorded without inspecting the saved JSON or an export.

This is a presentation and auditability gap only. It is not evidence that a runtime observation
occurred, and it must not change evidence levels, findings, gate decisions, final acceptance,
persistence, or exports.

## Chosen Design

Add one `Recorded at (UTC)` row to each existing bordered runtime-evidence card. Render the
Pydantic JSON representation of the stored timestamp so the value is explicit, timezone-aware,
stable, and consistent with persisted/exported data.

The row belongs beside the other record metadata, after the reviewer and before limitations.
No new control, schema field, helper, dependency, or formatting preference is introduced.

## Alternatives Considered

1. Hide the timestamp in an expander. Rejected because record chronology is core audit context,
   not optional detail.
2. Render a localized relative time. Rejected because values such as `two hours ago` are not
   reproducible and local timezone formatting can obscure the stored instant.
3. Leave the timestamp only in JSON/export. Rejected because it keeps the primary review surface
   incomplete.

## Verification

- Add a Streamlit AppTest with a fixed UTC timestamp and require the exact visible value.
- Keep existing complete-record, empty-limitations, and safe artifact-reference tests green.
- Run focused and adjacent Streamlit tests, Ruff, the complete offline suite, deterministic
  benchmark, `git diff --check`, and a loopback workbench health smoke.
- Verify the unchanged prerequisite and final-acceptance boundaries in the current browser. Do
  not submit invented runtime evidence solely to create a screenshot; use the AppTest render tree
  as authoritative evidence for the saved-record timestamp.

## Boundaries

The test fixture proves deterministic rendering only. It is not external PR runtime evidence,
user adoption, reviewer acceptance, or proof of correctness. No paid API or LLM, billing, fork,
organization, private repository, synthetic user, external write, release, or untrusted-code
execution is introduced.
