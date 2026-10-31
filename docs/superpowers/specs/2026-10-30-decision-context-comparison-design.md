# Recorded decision context in comparisons

## Intent and authority

After PR #232 the owner delegated selection and execution of one high-value automatic product
improvement, without personal testing or qualifying reviews. Live main is
`58c916016d5999b6ce6c1a37f0b612cc9beb663f`, clean with successful post-merge CI and no open PRs.
An independent gap audit confirmed that `_resolution_decisions` retains only decision enums.
Changing the note, asserted reviewer, timestamp, claimed level or linked runtime observation while
keeping that enum is invisible in current comparison output. This is a reporting omission, not
lost saved data or a gate defect.

## Approaches and selected scope

The agent selects a separate informational comparison projection under the owner's delegated
design authority. Expanding `changed_human_resolutions` would silently change existing enum-delta
semantics and benchmark expectations. A standalone historical-analysis viewer is useful but solves
a different inspection problem. Full resolution-event history and review-level final acceptance
are also outside this slice: compare the latest criterion resolutions and retained runtime records
already present in each validated analysis, and label that scope explicitly.

## Core contract

Add `scopeproof_core/reviews/decision_context_comparison.py`, independent of Streamlit/GitHub.
`DecisionContextComparison.from_bundles(previous, current)` reuses the existing compatible-bundle
validation. It projects repository/PR and two `DecisionContextSnapshot` objects containing owning
review ID, head, criteria revision (including historical `unknown`), input origin, full confirmed
criteria-source provenance, sorted criterion IDs, complete current `HumanResolution` records and
complete retained `RuntimeEvidence` records. Copies detach the source models. No artifact is
opened, fetched, executed, authenticated or re-verified.

Snapshots validate unique known criterion resolutions and runtime IDs, complete explicit nested
record fields (no projection-time default timestamps/actors), runtime owner scope, and the existing
linked criterion/reviewer/level relationship. Legacy all-null runtime identity stays unlinked;
live records still require scoped runtime identity. Canonical sorting ignores list order but retains
duplicates of genuinely unlinked observations rather than silently deduplicating them.

Derived `record_changes` compares criterion rows containing `resolution` and `runtime_evidence`.
Only criteria with recorded content appear. The distinctions are `identical_recorded_context`,
`only_previous`, `only_current`, and `recorded_context_changed`, based on complete canonical JSON
records, never semantic equivalence or verified behavior. Full previous/current records remain
inspectable even when their decision enums match. A computed link status distinguishes an explicit
runtime link, legacy manual verification without a link, and no link. Unlinked observations are
retained context, never attached to a decision by matching names, URLs, ordering or criterion alone.
Submitted computed fields are discarded and recomputed on parsing/export.

`ReviewComparison.decision_context_comparison` defaults to `None` for old comparison JSON. Missing
means unavailable, whereas a populated snapshot with no records means known empty. A computed
availability flag is never trusted from input. Cross-check each snapshot's review/head/revision,
criteria IDs/digest against its owning file-scope snapshot and both heads against the comparison.
When selected-reference context is present, repository/PR and full side provenance must agree.
Derived decision enum differences must agree with `changed_human_resolutions`; otherwise reject
the contradictory comparison rather than silently changing either view.

Keep `changed_human_resolutions`, candidate changes/counts, findings, imported JUnit context,
criteria-requiring-decision-review logic, final acceptance, scope and gates unchanged. This new
projection is non-gating reporting context even though the original runtime records may participate
in their original review's existing gate rules. Do not weaken original runtime validation.

## Presentation

Comparison JSON includes the validated snapshots and derived rows. Comparison Markdown and a
small workbench renderer show a separate **Recorded decision and runtime context** section, the
boundary text, both owning identities, each affected criterion, complete latest resolution fields
and retained runtime fields including limitations. Claim recorded results and asserted reviewers;
never claim ScopeProof executed or independently verified them. Show no-record and old-unavailable
states distinctly. Untrusted notes/actors/heads/results are inert text or escaped code; artifact
links use the existing safe reference renderer. Use neutral expander labels and wrapping code for
long identities. Render within the existing comparison authority guards; deferred saved-comparison
downloads continue checking full-record fingerprints and session leases at click time.

## Verification and boundaries

Construct same-enum changes in attribution, note, evidence URL/level, timestamp, linked runtime
ID/content/result/limitations, unlinked observations and missing contexts. Cover exact owners,
unknown revision, invalid links, mutable nested models, canonical ordering, computed-field
tampering, old comparison JSON, unsafe text/URLs, active/own-history/foreign-history comparisons,
saved-state changes and deferred downloads. Extend an installed-wheel restart/reopen/compare/
download journey, preserve original saved bytes and gates, and check desktop/phone/zoom geometry.
Run full 95% coverage, lint/lock checks, deterministic benchmarks, clean installed-wheel checks,
available Python/Windows CI, independent whole-branch review, exact-head guarded merge and main CI.

Record new constructed cases separately. Do not modify the seven frozen R-002 files or historical
benchmark labels/results, persisted record v7, public v0.2.4 or the historical private candidate.
Source remains unreleased 0.2.5. Stage 1 stays closed at zero, Stage 2 owner-led and Stage 3 dormant.
No personal testing, qualifying reviews, release, deployment, outreach, new adapter or standing
feature queue follows. Independent usefulness and genuine use remain unknown.
