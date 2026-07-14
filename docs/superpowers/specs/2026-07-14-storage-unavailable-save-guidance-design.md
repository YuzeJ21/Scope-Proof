# Storage-Unavailable Save Guidance Design

## Context

ScopeProof validates the local review directory before offering storage actions. If the directory
is unsafe or unavailable, reopening and saving are correctly disabled. The only explanation is
currently rendered inside the collapsed **Reopen saved review** panel. After a user completes an
analysis, the summary therefore shows an unsaved review and a disabled **Save local review** button
without explaining the disabled state at the point of action.

This is a recovery-guidance gap, not a persistence failure or data-integrity gap. The review remains
in session memory and all three exports remain available.

## Decision

When a review summary is present and the validated local review store is unavailable, render one
warning immediately before the Save control:

> Local saving is unavailable. The current review remains open as unsaved work, and exports remain
> available. Verify that the ScopeProof review directory is a regular local directory; ScopeProof
> will recheck it on the next interaction.

Keep the Save button disabled. Keep the existing storage error in the reopen panel because it
explains why reopening is unavailable before a review exists.

## Boundaries

- Do not attempt to repair, replace, create, or delete the review directory.
- Do not expose the directory path or raw exception details.
- Do not mutate the current review, saved fingerprint, bundle, or gate.
- Do not disable Markdown, JSON, or CSV exports.
- Do not change `JsonReviewStore`, schemas, persistence formats, CLI behavior, or release identity.
- Do not add billing, paid APIs, background work, or GitHub notification behavior.

## Verification

Regression coverage must use controlled unsafe-store fixtures and prove that:

1. the point-of-action warning is visible after analysis;
2. Save remains disabled;
3. the exact review remains open and unsaved;
4. all three exports remain available;
5. no local path or raw exception is rendered; and
6. normal available-storage behavior remains unchanged.
