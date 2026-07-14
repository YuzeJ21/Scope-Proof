# Runtime Evidence Event Boundary Design

## Problem

`append_runtime_evidence()` revalidates the review state but trusts the supplied
`RuntimeEvidence` instance. Pydantic assignment validation is not enabled, so a
caller can mutate a previously valid object into invalid evidence and append it.
The function also appends the caller-owned object directly, allowing later caller
mutation to corrupt the returned state through aliasing.

## Decision

Reconstruct the supplied runtime evidence through `RuntimeEvidence.model_validate()`
before reading its criterion target. Append that newly validated instance to the
deep-copied active bundle. Existing bundle and criterion guards remain unchanged.

This keeps runtime evidence append-only, manual, and unable to upgrade static
findings or gate truth. It adds no execution, inference, paid service, or UI logic.

## Verification

Regression tests must prove that a valid-then-mutated evidence object is rejected
and that mutating the caller's object after append cannot alter returned state.
Existing lifecycle and runtime evidence flows remain green, followed by Ruff, the
full offline suite, deterministic benchmark, clean-wheel installed probes,
packaged workbench health, and independent review.
