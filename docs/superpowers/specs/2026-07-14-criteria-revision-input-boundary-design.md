# Criteria Revision Input Boundary Design

## Problem

`revise_criteria()` revalidates the existing review state but passes caller-owned
`Criterion` instances directly into `CriteriaRevision`. Because nested Pydantic
instances are trusted by default, a valid-then-mutated criterion can enter the
returned state, and later caller mutation can alter the revision through aliasing.

## Decision

Reconstruct every supplied criterion through `Criterion.model_validate()` before
creating the revision. The reconstructed list is both schema-validated and
independent from caller-owned objects. Existing source-text validation, revision
numbering, analysis history, and confirmation behavior remain unchanged.

The change stays in the core lifecycle boundary and does not normalize or invent
user requirements.

## Verification

Regression tests first prove mutated-input acceptance and post-revision aliasing.
Then run focused lifecycle/schema/storage/export coverage, Ruff, the full offline
suite, deterministic benchmark, clean-wheel probes, packaged workbench health,
independent review, and protected GitHub integration.
