# Evidence-delta and first-use maturity design

Status: authorized by the 2026-07-26 evidence-quality goal and implemented only through narrow,
reviewer-controlled changes.

## Goal

Make changed-head evidence review the clearest return-use path while reducing avoidable first-use
friction. Preserve explicit criteria confirmation, deterministic candidates, externally recorded
runtime evidence, and human acceptance as separate states.

## Evidence-delta behavior

- Display the loaded, previous, and current head SHAs wherever their distinction matters.
- Warn before invalidating a reopened review when the PR head changed.
- Never carry a previous resolution or final acceptance into the new head.
- Compare immutable references as Unchanged, Relocated, Modified, Added, or Removed.
- Show previous and current references together for paired changes.
- Count all five change classes, including Unchanged.
- Explicitly identify prior decisions that require a new review.
- Keep comparison language bounded to candidate references, not criterion correctness.

## Evidence matrix behavior

- Add a compact Strong, Weak, None, and Incomplete candidate-strength summary.
- Add an unresolved-criteria queue with the finding's current recommended action.
- Keep the full criterion matrix, evidence type, reviewer decision, filters, and detail view.
- Keep retrieval diagnostics separate from evidence and from missing-evidence conclusions.

## First-use behavior

- Keep the deliberately constructed demo before the public-PR form.
- Keep the five-stage primary path visible above the fold.
- Use state-aware sidebar next actions.
- Preserve the verified v0.2.1 wheel as the public install path until a separate release decision.
- Describe under five minutes as an unvalidated target for an inspectable report.
- Describe under ten minutes as the Stage 1 gate for a completed human review.
- Do not add timers, hosted processing, automatic acceptance, or bypass criteria confirmation.

## Self-review

The design changes presentation and comparison metadata only. It does not change retrieval
tokenization, thresholds, ranking, evidence levels, gate decisions, persistence authority, or
external publication. Every new computed comparison field is Pydantic-validated and deterministic.
