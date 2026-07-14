# Review-store root type guard design

## Verified defect

On current `main`, when the configured review-store path already exists as a regular file, `list_review_ids()` returns an empty list. The Streamlit workbench therefore marks storage as available. A later save reaches `Path.mkdir(..., exist_ok=True)` and raises an unhandled `FileExistsError`.

## Root cause

The core store safety assertion rejects a direct symbolic link but does not reject other existing non-directory filesystem objects. Discovery separately treats every non-directory path as an absent store, so the UI cannot distinguish an absent directory from an unusable existing path.

## Scope and constraints

- Reject any configured store root that exists but is not a directory.
- Preserve the existing direct-symlink rejection and its specific error.
- Preserve absent-directory discovery as an empty store so first save can create it.
- Apply the guard consistently to list, load, and save.
- Reuse the existing recoverable Streamlit storage state; do not duplicate the core rule in the UI.
- Do not claim protection against hostile filesystem races or symbolic links in ancestor paths.

## Selected approach

Extend `JsonReviewStore._require_safe_directory()` with one ordered type check after the symlink check: if the configured path exists and is not a directory, raise `UnsafeReviewStore`. The existing Streamlit startup handler already treats that exception as unavailable storage, displays actionable guidance, and disables reopen/save.

The ordered checks retain the more precise symbolic-link error, including for links whose targets are missing or not directories.

## Verification

- Core tests prove list, load, and save reject a regular-file store root.
- AppTest proves the workbench shows the existing recovery state and disables storage actions.
- Existing tests continue to prove absent directories work and direct symlinks are rejected.
- Full Ruff, pytest, deterministic benchmark, clean-wheel, and installed-package probes remain required.
