# Mobile Evidence Matrix Accessibility Design

## Problem evidence

At a fresh 390×844 local viewport, the constructed demo evidence matrix renders a six-column
Markdown table about 649 pixels wide inside a 347-pixel content block. The containing elements use
visible overflow while the application shell clips the overflow. The rightmost Evidence types and
Reviewer decision columns therefore cannot be reached from the visible mobile page.

This is current-run browser evidence from the local v0.2.2 candidate. It is a responsive-layout and
information-access defect, not participant, customer, runtime-correctness, or Stage 1 evidence.

## Constraints

- Preserve all six columns, deterministic ordering, filters, labels, and reviewer-first language.
- Do not modify core evidence, gate, schema, persistence, comparison, or export behavior.
- Keep repository-controlled criterion text inert; do not introduce raw HTML rendering.
- Provide a visible small-screen instruction without claiming full accessibility compliance.
- Keep the change local-only; do not publish, push, create a PR, or generate notifications.

## Considered approaches

### 1. Responsive stacked cards

Render one mobile card per criterion while retaining the table on desktop. This is visually clear
but duplicates the matrix presentation, adds breakpoint-specific behavior, and increases the risk
that a field or label diverges between views.

### 2. Streamlit data grid with horizontal access — selected

Render the existing ordered matrix records with `st.dataframe`, hide the index, and stretch the
grid to the available container. Streamlit owns escaping, keyboard interaction, and horizontal
scrolling. Add one short caption telling small-screen reviewers that all six columns remain in the
grid and that the rightmost columns may require horizontal scrolling.

This is the smallest solution that preserves every field without adding an unsafe HTML boundary or
maintaining two presentations.

### 3. Hide lower-priority columns on mobile

Remove Evidence types or Reviewer decision below a breakpoint. This reduces width but hides exactly
the audit information reviewers need, so it is rejected.

## Detailed design

Replace only the Markdown-table construction and rendering in `apps/web/app.py`. Continue building
the current `matrix: list[dict[str, str]]` in criterion order, then render:

```python
st.caption(
    "All six evidence columns remain available. On smaller screens, scroll the table "
    "horizontally to inspect Evidence types and Reviewer decision."
)
st.dataframe(matrix, hide_index=True, use_container_width=True)
```

Do not change filter behavior or the existing empty-result message. When filters return no rows,
render the empty grid with the same six named columns or retain the current empty-result notice in a
way that keeps the column contract deterministic.

## Testing

Update the focused Streamlit regression so it requires exactly one data grid and verifies:

- column order is Criterion, Requirement, Priority, Evidence status, Evidence types, Reviewer
  decision;
- AC-01 through AC-04 retain their existing values and order;
- the rightmost Evidence types and Reviewer decision values are present;
- the small-screen horizontal-scroll caption is present;
- matrix filtering and the no-results message remain unchanged.

Run the focused AppTest regression RED before implementation and GREEN afterward. Then run the
complete Streamlit test file, Ruff, and diff hygiene. Finally repeat fresh 1280×720 and 390×844
local screenshots. The mobile screenshot must show a container-width grid with reachable rightmost
columns rather than clipped document overflow.

## Non-goals

- No redesign of criterion detail, runtime evidence, reviewer decisions, or exports.
- No new matrix sorting, editing, paging, selection, or download capability.
- No core-engine or schema change.
- No claim of WCAG conformance or genuine participant validation.
