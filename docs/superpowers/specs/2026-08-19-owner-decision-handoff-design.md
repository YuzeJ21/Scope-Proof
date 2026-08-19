# Owner Decision Handoff Design

Date: 2026-08-19

Status: approved by the owner for implementation on 2026-08-19

## Context

PR #197 completed the first owner-led Stage 2 workflow consolidation and merged as
`789950dc63d80ec24d8bca5974a3ae52955b1c4f`. It added a stable unresolved-criteria
queue whose actions select the matching criterion. The selected criterion and its
decision controls still render after the optional global evidence matrix, however.
The action therefore changes the correct state but leaves the owner to move through
secondary material before reaching the control named by the action.

The queue also follows confirmed-criterion order even when later unresolved
must-have criteria are actively blocking the deterministic gate. The default
criterion detail follows the first confirmed criterion rather than the first
unresolved blocker.

The authoritative roadmap and current status document still describe the PR #197
owner-workflow consolidation as future work even though the merge and its
resulting-main checks are complete.

## Goal

Complete the owner decision handoff so an unresolved blocking criterion is the
first stable target, the selected criterion evidence and decision controls appear
before the secondary global matrix, and current operating documents record the
merged PR #197 truth.

## User flow

After deterministic analysis, the review page presents these numbered sections:

1. `1 · Start Review`
2. `2 · Confirm Criteria`
3. `3 · Decision Progress`
4. `4 · Criterion Review`
5. `5 · Evidence Matrix`
6. `6 · Summary & Export`

Within Decision Progress, unresolved blocking criteria appear first. Ordering is
stable within the blocking and non-blocking groups, so confirmed criterion order
is not otherwise rewritten. Activating `Open <criterion> decision controls`
selects that criterion. Criterion Review then renders the selected requirement,
evidence status, diagnostics, candidate evidence, human-resolution control, and
optional externally recorded E3/E4 workflow before the global matrix.

The Evidence Matrix remains available as a secondary all-criteria overview with
the same filters, cards, widget keys, and selection actions. Final review
acceptance remains after the all-criteria matrix because it is a review-level event,
not an individual-criterion shortcut.

## Presentation model

Add one pure presentation helper:

```python
def prioritize_unresolved_criterion_ids(
    *, unresolved_ids: list[str], blocking_ids: set[str]
) -> list[str]:
    """Return blockers first while preserving order within both groups."""
```

The helper performs a stable partition only. It does not calculate gate status or
rewrite criteria. `default_criterion_detail_id` chooses the first unresolved
blocker, then the first unresolved criterion, then the first confirmed criterion
whenever the existing selection is absent or invalid.

## Evidence and trust boundaries

- ScopeProof remains an evidence assistant, not a correctness oracle.
- Static implementation or test candidates never become runtime verification.
- Reviewer-confirmed criteria remain mandatory before analysis.
- No target-repository code is executed.
- No core gate, evidence-level, human-decision, final-acceptance, comparison,
  schema, persistence, export, or GitHub Action behavior changes.
- Reviewer identity remains asserted rather than authenticated.
- The GitHub Action remains opt-in and informational.
- Failed lifecycle actions continue to leave the saved review unchanged.
- False Ready remains more harmful than False Blocked.
- Stage 1 remains closed and not pursued, with all five measurements at zero.
- This is owner-led Stage 2 engineering evidence only. It does not create customer
  validation, accessibility conformance, production evidence, or Stage 3 authority.

## Verification

Test-driven regressions must prove:

- blocker-first ordering is stable;
- an absent or invalid selected criterion defaults to the first unresolved blocker;
- queue actions remain available independently of evidence-matrix filters;
- the selected criterion and resolution widgets occur before matrix filters in the
  rendered Streamlit element tree;
- the installed-wheel Chromium path selects AC-02 and renders its Human decision
  control before the matrix filter at both 1280×720 and 390×844;
- the six numbered workbench sections remain in the intended order;
- current authoritative documents record exact PR #197 head, merge, and hosted
  resulting-main evidence without claiming customer validation.

Final verification includes Ruff, the complete suite with at least 95% combined
coverage, repository contracts, deterministic and comparison benchmarks, installed
wheel/browser evidence, and independent review.

## Non-goals

- Changing the documented low-evidence human-acceptance override policy.
- Changing deterministic gates, evidence thresholds, or acceptance semantics.
- Adding authentication, accounts, billing, private repositories, hosted source
  processing, generic review, security scanning, automatic fixes, or paid APIs.
- Starting Stage 3, reopening Stage 1, contacting participants, or performing
  commercial outreach.
- Releasing, tagging, publishing, deploying, or merging this work without a
  separate owner decision.
