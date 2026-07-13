# Evidence Matrix Filter Completion Design

## Problem

The accepted MVP workflow requires the evidence matrix to filter findings by blocker, status,
priority, and evidence level. The current Streamlit workbench exposes only status and priority.
Reviewers cannot isolate gate-blocking criteria or compare findings at a particular evidence level,
which adds avoidable scanning during first use.

## Decision

Add two deterministic controls beside the existing filters:

- `Show blocking criteria only`, a checkbox backed only by `bundle.gate.blocking_criteria`.
- `Filter evidence level`, a multiselect over the existing `EvidenceLevel` enum.

All active filters combine with AND semantics. The controls filter presentation only; they do not
recalculate findings, evidence, human resolutions, or the gate. When no rows match, keep the matrix
header visible and show `No criteria match the current filters.` so the reviewer knows to clear or
change filters.

## Alternatives Considered

1. A gate-role multiselect with blocking/non-blocking values. Rejected because the MVP names blocker
   filtering, and a checkbox is more direct for the primary review task.
2. A generic query builder. Rejected as unnecessary complexity for four bounded fields.
3. Checkbox plus evidence-level multiselect. Selected because it follows existing control patterns
   and uses authoritative stored values without new semantics.

## Safety and Verification

The change is Streamlit-only and does not alter persisted or exported data. AppTest regressions will
prove both controls exist, blocker filtering is derived from `gate.blocking_criteria`, evidence-level
filtering matches `Finding.evidence_level`, filters combine, and the empty state appears. Verification
includes Ruff, full pytest, deterministic benchmark, and installed Streamlit HTTP health plus focused
rendered AppTests. No API, billing, dependency, telemetry, or untrusted code execution is added.
