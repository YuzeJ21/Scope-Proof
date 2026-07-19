# Mobile Evidence Matrix Accessibility Design

## Problem evidence

At a fresh 390×844 local viewport, the constructed demo evidence matrix renders a six-column
Markdown table about 649 pixels wide inside a 347-pixel content block. The containing elements use
visible overflow while the application shell clips the overflow. The rightmost Evidence types and
Reviewer decision columns therefore cannot be reached from the visible mobile page.

This is current-run browser evidence from the local v0.2.2 candidate. It is a responsive-layout and
information-access defect, not participant, customer, runtime-correctness, or Stage 1 evidence.

## Constraints

- Preserve all six fields, deterministic ordering, filters, labels, and reviewer-first language.
- Do not modify core evidence, gate, schema, persistence, comparison, or export behavior.
- Keep repository-controlled criterion text inert; do not introduce raw HTML rendering.
- Keep every field visible at small widths without claiming full accessibility compliance.
- Keep the change local-only; do not publish, push, create a PR, or generate notifications.

## Considered approaches

### 1. Responsive evidence cards — selected after review

Render one card per criterion at every viewport. Each card exposes the same six fields in the same
order. This avoids breakpoint-specific duplication, horizontal clipping, and hidden interactions.
Requirement text uses `st.text` so repository-controlled content remains inert.

### 2. Streamlit data grid with horizontal access — rejected after review

Render the existing ordered matrix records with `st.dataframe`, hide the index, and stretch the
grid to the available container. Streamlit owns escaping, keyboard interaction, and horizontal
scrolling. Add one short caption telling small-screen reviewers that all six columns remain in the
grid and that the rightmost columns may require horizontal scrolling.

Browser review showed that the grid also introduces column sorting, search, column hiding,
fullscreen, and CSV download. Those are outside this bounded accessibility change. The proposed
`width="stretch"` parameter also fails on the declared Streamlit 1.37 dependency floor. The grid is
therefore rejected rather than broadening the product or dependency contract.

### 3. Hide lower-priority columns on mobile

Remove Evidence types or Reviewer decision below a breakpoint. This reduces width but hides exactly
the audit information reviewers need, so it is rejected.

## Detailed design

Replace only the Markdown-table construction and rendering in `apps/web/app.py`. Continue building
the current `matrix: list[dict[str, str]]` in criterion order. When rows exist, render one bordered
container per row:

```python
st.caption(
    "Each evidence card preserves the criterion, requirement, priority, evidence "
    "status, evidence types, and reviewer decision without hiding mobile content."
)
for row in matrix:
    with st.container(border=True):
        st.markdown(f"**Criterion:** {row['Criterion']}")
        st.caption("Requirement")
        st.text(row["Requirement"])
        st.caption(f"Priority: {row['Priority']}")
        st.caption(f"Evidence status: {row['Evidence status']}")
        st.caption(f"Evidence types: {row['Evidence types']}")
        st.caption(f"Reviewer decision: {row['Reviewer decision']}")
```

Do not change filter behavior or the existing empty-result message. When filters return no rows,
render only the current empty-result notice.

## Testing

Update the focused Streamlit regression so it requires evidence cards and verifies:

- no data grid or legacy Markdown evidence table remains;
- every card exposes Criterion, Requirement, Priority, Evidence status, Evidence types, and Reviewer
  decision;
- AC-01 through AC-04 retain their existing values and order;
- Evidence types and Reviewer decision values are present without horizontal access;
- matrix filtering and the no-results message remain unchanged.

Run the focused AppTest regression RED before implementation and GREEN afterward. Then run the
complete Streamlit test file, Ruff, and diff hygiene. Finally repeat fresh 1280×720 and 390×844
local screenshots. The mobile screenshot must show cards whose complete contents stay inside the
document width.

## Non-goals

- No redesign of criterion detail, runtime evidence, reviewer decisions, or exports.
- No new matrix sorting, editing, paging, selection, or download capability.
- No core-engine or schema change.
- No claim of WCAG conformance or genuine participant validation.
