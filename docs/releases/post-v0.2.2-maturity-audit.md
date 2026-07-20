# ScopeProof post-v0.2.2 maturity audit

Date: 2026-07-20

Status: **Internal engineering audit; not customer or market validation**.

This audit evaluates the implemented first-use and re-review workflow at source commit
`22594c364ec9c165aca264e186a9af325ea2bcab`, with the candidate verification record on local commit
`2ac9fddce3bc013af99f5dee63a28e6e702f4321`. It does not publish, contact users, execute pull-request
code, or award Stage 1 credit.

## Product-flow audit

| Step | Observed behavior | Health | Remaining evidence limit |
| --- | --- | --- | --- |
| Start review | The workbench leads with the evidence-assistant boundary, public-PR input, visible constructed demo, session-only-token boundary, and local-storage explanation. | Healthy | A genuine participant has not demonstrated discoverability or setup time. |
| Confirm criteria | Normalized atomic criteria, priority, required evidence level, add/split/remove controls, and an explicit confirmation gate are visible before analysis. | Healthy | Source-owner comprehension has not been observed in a genuine session. |
| Evidence matrix | Observed CI, runtime-verification absence, candidate status, evidence type, priority, and unresolved reviewer decision remain distinct. Desktop and 390-by-844 captures preserve readable content without hiding audit fields. | Healthy | Screenshot inspection does not prove keyboard, screen-reader, zoom, or full WCAG conformance. |
| Criterion detail | Each criterion exposes required versus observed evidence, confidence, candidate count, recommended next action, citations, external-verification fields, and a separate human resolution. | Healthy | Candidate usefulness and misleading-match rates still require genuine reviewers. |
| Summary and export | The unsaved-review warning, review ID reliance boundary, deterministic gate reasons, next actions, and Markdown, JSON, and CSV downloads are visible. The CLI additionally supports validated HTML export. | Healthy | Export usefulness to another practitioner has not been observed. |
| Changed-SHA re-review | Tests and the constructed comparison benchmark preserve immutable previous/current bundles and cover Added, Modified, Relocated, Removed, and Unchanged evidence. | Engineering-verified | No genuine participant has used re-review after a real PR head change; this audit did not mutate a public PR to manufacture that evidence. |

Local browser captures were inspected during this audit and intentionally kept outside the tracked
source tree. They are engineering inspection aids, not release assets or participant evidence.

## Prioritized maturity gaps

No confirmed P0 or P1 product defect was found. The remaining gaps are evidence and adoption gaps:

1. **P1 — Genuine first-use evidence:** obtain one qualifying non-owner review with exact public
   inputs, saved output, timing, friction, participant-selected outcome, and reuse intent.
2. **P1 — False Ready observation:** maintain zero confirmed False Ready across genuine reviews;
   benchmark success cannot substitute for this measurement.
3. **P2 — Real changed-head use:** observe whether a participant notices and acts on changed,
   relocated, removed, added, and unchanged evidence after the reviewed SHA changes.
4. **P2 — Assistive-technology verification:** perform keyboard-only, focus-order, screen-reader,
   zoom, and contrast testing when a repeatable human accessibility review is available.
5. **P3 — Export handoff:** observe whether another practitioner can understand the exported
   identity, evidence boundary, missing evidence, decisions, and gate without the facilitator.

These gaps do not justify broad integrations, paid AI, accounts, private repositories, billing, or
weaker deterministic gates.

## Market-positioning refresh

Official documentation was rechecked for Qase requirements and traceability, Azure DevOps
end-to-end traceability, TestRail's specification-first workflow, and GitHub Copilot code review.
No material change invalidated the current positioning record. The bounded product inference is
that adjacent products are stronger in test management, lifecycle linking, or general code-review
feedback. ScopeProof's still-unproven position is the narrower combination of confirmed criteria,
inspectable PR candidates,
missing-evidence explanations, deterministic conservative gates, attributable human decisions,
and immutable-head re-review.

This comparison verifies adjacent capabilities, not ScopeProof differentiation, demand, buyer,
price, or willingness to pay.

## Stage readiness

The one-time public intake check found no non-owner submission or completed outcome. Current counts
are therefore: 0 genuine completed reviews, 0 independent practitioners, 0 represented public
repositories, 0 participant sessions under ten minutes, 0 confirmed False Ready outcomes across 0
participant reviews, 0 reuse-intent signals, and 0 voluntary team-price discussions. The absence
of observed False Ready is not a validated rate when no qualifying review exists.

| Stage | Prepared internal capability | Current status | Entry evidence still required |
| --- | --- | --- | --- |
| Stage 1 — Genuine public alpha | Intake qualification, participant quickstart, outcome schema, facilitator checklist, local review persistence, exports, and conservative benchmarks. | Waiting | Five genuine reviews, three independent practitioners, three public repositories, three under-ten-minute participant results, zero confirmed False Ready, and two reuse-intent signals. |
| Stage 2 — Commercial discovery | Research questions, price hypotheses, falsification rules, and stop gates are documented. | Gated | Every Stage 1 condition plus completed-use evidence for repeat intent and voluntary team-price discussion. |
| Stage 3 — Limited beta | Unassisted-repeat-use, changed-SHA re-review, comprehension, reliability, and False Ready exit criteria are documented. | Gated | Stage 1 and Stage 2 completion plus a separate owner decision and genuine repeat use. |
| Stage 4 — Evidence-guided expansion | Collaboration, richer import, and team-workflow ideas are retained as a gated backlog. | Gated | Repeated genuine use that proves a specific expansion need and a separate scope decision. |

## Exact waiting condition

Waiting for a non-owner participant with a genuine public PR, public/source-owner-confirmed
criteria, exact head SHA, saved ScopeProof review, outcome/time/friction, and reuse-intent signal.
