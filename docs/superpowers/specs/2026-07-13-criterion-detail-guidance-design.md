# Criterion Detail Guidance Design

## Problem

A current-browser audit of the deterministic demo confirmed that Criterion Detail exposes provisional
status, finding reason, missing evidence, immutable links, excerpts, relevance text, and limitations.
It does not show the finding's stored `recommended_action`, does not locally label matched items as
candidate evidence, and omits each item's deterministic `matching_rule`. The relevance reason is also
unlabeled. A reviewer therefore has weak recovery guidance and must infer why an item appeared.

## Decision

Complete the existing detail contract from validated fields only:

- Show `Recommended next action` followed by `Finding.recommended_action` for every criterion.
- Add a `Candidate evidence` heading before evidence expanders.
- When `Finding.evidence_ids` is empty, show `No candidate evidence is linked to this provisional finding.`
- Within each expander, label `EvidenceItem.relevance_reason` as `Matching rationale` and show
  `EvidenceItem.matching_rule` as `Matching rule`.
- Keep every limitation visibly labeled and preserve the immutable permalink and excerpt.

The section remains above manual runtime evidence so candidate implementation/test evidence cannot be
confused with separately supplied runtime observations.

## Alternatives Considered

1. Add only recommended action. Rejected because it leaves candidate status and deterministic matching
   provenance ambiguous in the same bounded surface.
2. Move guidance into the global summary. Rejected because criterion-specific recovery belongs beside
   the finding it explains.
3. Complete the existing detail surface from stored fields. Selected because it satisfies the accepted
   reporting contract without adding inference, state, or visual-system changes.

## Safety and Accessibility

- No evidence retrieval, scoring, verification, lifecycle, resolution, or gate behavior changes.
- No new schema, dependency, API, billing, network, telemetry, or untrusted code execution.
- Visible headings and labels improve reading order and assistive-technology clarity; screenshots alone
  do not establish full WCAG compliance.
- Implementation/test evidence stays candidate evidence and is never presented as runtime proof.

## Verification

AppTest regressions will require recommended guidance for evidence-found and missing states, candidate
heading/empty state, matching rationale/rule labels, immutable link, excerpt, and limitations. Broad
verification includes Ruff, full pytest, deterministic benchmark, installed-wheel Streamlit health,
and a same-state browser screenshot comparison after implementation.
