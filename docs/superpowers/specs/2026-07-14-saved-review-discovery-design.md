# Saved-review discovery design

## Problem

ScopeProof persists validated reviews locally and can reopen a review by ID, but a fresh app session renders only a blank ID field. A user who did not separately retain the opaque review ID must inspect `~/.scopeproof/reviews` outside the product. A browser audit with a schema-valid `audit-saved-review.json` record confirmed that the record is not visible in the reopen flow.

## Constraints

- Keep review storage local-first and free of paid services.
- Do not load, trust, or execute record contents merely to discover them.
- Continue validating the complete persisted object when the user opens a record.
- Do not follow symlinks or expose files outside the app-owned review directory.
- Keep ordering deterministic and preserve the existing unsaved-review replacement guard.
- Do not turn this into record management, deletion, search, or migration work.

## Considered approaches

### A. Display filenames as copyable text

This is small, but it retains copy-and-paste friction and leaves the reopen action disconnected from the discovered records.

### B. Enumerate safe IDs and select one in the existing reopen flow

Add a deterministic storage query that returns only valid IDs belonging to regular, non-symlink `.json` files. When records exist, render them in a select box; otherwise retain the manual ID field and the existing missing-record recovery path. Opening still calls `JsonReviewStore.load`, so record version and Pydantic validation remain authoritative.

This is the selected approach.

### C. Build a local record browser

Metadata previews, search, deletion, and migration would add state-management and privacy surface without evidence that they are needed for the first-use adoption gap.

## Storage contract

`JsonReviewStore.list_review_ids()` returns a sorted list of record identifiers. It:

- returns an empty list when the directory does not exist;
- considers only direct `*.json` children;
- ignores symlinks and non-files;
- ignores stems that do not satisfy the existing review-ID grammar;
- does not parse or validate record contents.

The method discovers candidate local records, not validated review state. `load()` remains the only path that validates record version and nested Pydantic models.

## Interface behavior

- The existing collapsed `Reopen saved review` section remains a secondary path.
- If saved IDs exist, a `Saved review ID` select box lists them in deterministic order and starts with no selection.
- Supporting copy states how many local records were found and that a record is validated when opened.
- If no IDs exist, the existing `Review ID` text field remains available, with an explicit no-saved-record message. This preserves safe recovery for a known or missing ID without presenting an empty select box.
- `Reopen local review` stays disabled until an ID is selected or entered, and it also remains subject to the unsaved-review replacement guard.
- Existing load error messages remain unchanged for missing, unsupported, corrupt, or invalid records.

## Verification

- Storage regression tests cover absent directories, deterministic ordering, and rejection of symlink, invalid-name, and non-JSON entries.
- Streamlit AppTest covers empty-state behavior, discovery in a fresh session, selection and reopening, and the replacement guard.
- The full source suite, Ruff, benchmark, clean-wheel checks, and a live in-app browser pass verify the release-shaped behavior.
