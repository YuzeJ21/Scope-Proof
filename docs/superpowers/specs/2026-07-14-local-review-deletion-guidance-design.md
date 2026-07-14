# Local Review Deletion Guidance Design

## Problem

ScopeProof now supports deleting one exact app-owned saved review through both
the workbench and `scopeproof delete`, but the README's local-storage section
only explains discovery, validation, reopening, and persistence safety. A new
user reading the primary public onboarding document cannot discover the
deletion path without following the separate privacy-readiness link or reading
CLI help.

Current runtime evidence shows that the product flow itself is healthy: a saved
record appears in the collapsed `Reopen saved review` panel, deletion controls
appear only after selection, the delete button stays disabled until explicit
confirmation, and success returns the panel to the empty state. CLI help also
lists the exact single-record command. The gap is public guidance, not product
behavior.

## Outcome

Extend the existing README `Local review storage` section with the shortest
accurate deletion path for both supported surfaces:

- in the workbench, select a listed record and confirm permanent deletion;
- in the CLI, run `scopeproof delete REVIEW_ID` and use `--storage-dir PATH`
  only when the review was saved outside the default CLI directory.

Keep the boundary explicit: deletion removes only the selected app-owned JSON
record. It does not remove exported reports, storage backups, or an open
in-memory review, and it is not a secure-erasure guarantee.

## Approaches considered

### Keep the privacy-readiness link as the only guidance

This avoids README growth but leaves a primary first-use workflow undiscoverable
in the document that already explains local review storage.

### Add a dedicated deletion section

This is easy to find but gives a small secondary action too much hierarchy and
duplicates the privacy document.

### Extend the existing storage paragraph — selected

This places the action beside save/reopen behavior, preserves the README's
current hierarchy, and needs only a concise pointer to the detailed privacy
boundary.

## Documentation contract

Add a repository-contract regression that requires the README to contain:

- the literal command `scopeproof delete REVIEW_ID`;
- the exact workbench confirmation label
  `Permanently delete the selected local review`;
- language that exported reports remain user-owned and are not removed;
- language that deletion is not secure erasure.

The contract must not assert formatting or duplicate implementation details.
Existing privacy-readiness and workflow contract tests remain unchanged.

## Verification

Follow regression-first development: add the README contract, observe it fail,
then update the README and observe it pass. Run the complete repository-contract
tests, Ruff, the offline suite, deterministic benchmark, and `git diff --check`.
Because this slice changes documentation only, the already captured exact-main
workbench interaction is the runtime evidence; do not represent the README edit
as new product-runtime verification.

## Non-goals

- Changing deletion, storage, CLI, Streamlit, schema, evidence, lifecycle, or
  gate behavior.
- Adding bulk deletion, directory deletion, secure erasure, backup management,
  hosted storage, private repositories, billing, or paid APIs.
- Creating a release, issue comment, fork test, or external validation claim.
