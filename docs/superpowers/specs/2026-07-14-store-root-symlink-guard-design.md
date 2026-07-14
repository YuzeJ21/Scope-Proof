# Review-store root symlink guard design

## Verified defect

`JsonReviewStore` rejects a symlinked record file, but it accepts the configured review directory itself when that directory is a symlink. A temporary-directory reproduction on current `main` pointed `reviews` at a sibling `outside` directory; `list_review_ids()` returned `outside-review`. The same root is used by load and save, so the direct directory symlink defeats the intended local-store boundary.

## Scope and constraints

- Refuse an already-present symbolic link at the configured store-directory path for list, load, and save.
- Do not parse or migrate records while checking the directory.
- Give the Streamlit user a recoverable storage error instead of an application traceback.
- Disable reopen and save actions while the configured store is unsafe or unavailable.
- Preserve normal directories, absent directories, record-file symlink rejection, and deterministic listing.
- This slice does not claim to solve hostile filesystem races or symbolic links in every ancestor path.

## Selected approach

Add `UnsafeReviewStore`, a `ValueError` subtype, and a private store-root assertion. The assertion checks `Path.is_symlink()` before every list, load, or save path. A direct symlink raises the explicit error before traversal or directory creation.

At Streamlit startup, discover saved IDs inside a narrow `UnsafeReviewStore`/`OSError` handler. If discovery fails, show one actionable error inside the existing reopen expander, hide the ID controls, and keep the reopen action disabled. The same availability flag disables `Save local review`, preventing a known-unsafe store from reaching the save path.

The core remains authoritative. UI behavior is recovery guidance, not the security control.

## Alternatives rejected

- Returning an empty list for a symlinked directory would hide the boundary violation and still leave load/save inconsistent.
- Resolving the symlink and treating the target as trusted would silently expand the configured storage boundary.
- Rebuilding persistence around directory file descriptors and no-follow flags would address a broader race model but is disproportionate to the reproduced direct-symlink defect.

## Verification

- Core tests prove list, load, and save reject a symlinked store root and preserve record-file symlink handling.
- AppTest proves the workbench renders recovery guidance without a traceback and disables reopen/save.
- Full Ruff, pytest, deterministic benchmark, clean-wheel, and installed-package probes remain required.
