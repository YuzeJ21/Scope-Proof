# Review Bundle Cross-Reference Integrity Implementation Plan

**Goal:** Reject persisted or exportable review bundles with ambiguous, dangling, or
cross-criterion references before they can crash an exporter or misassociate evidence.

**Architecture:** Add one after-validation graph check to the core `ReviewBundle` Pydantic model.
Keep retrieval, verification, lifecycle, exporters, gate semantics, and UI unchanged.

## Constraints

- Keep validation deterministic and error messages stable.
- Do not silently repair, drop, reorder, or deduplicate persisted data.
- Do not require all candidate evidence to be referenced.
- Do not change gate precedence, evidence levels, permissions, or user-visible workflows.
- Do not create issue comments, reviewer requests, releases, fork tests, or notification-only work.

### Task 1: Add regression-first bundle graph tests

**File:** Create `tests/schemas/test_review_bundle_integrity.py`.

1. Build one minimal valid bundle fixture.
2. Prove the valid bundle survives JSON round trip.
3. Add failing cases for duplicate criterion IDs, duplicate evidence IDs, evidence attached to an
   unknown criterion, duplicate/missing/extra findings, dangling evidence links, cross-criterion
   evidence links, and duplicate finding evidence references.
4. Add failing cases for unknown runtime-evidence criteria, duplicate or unknown active
   resolutions, and duplicate or unknown criterion references in each gate list.
5. Run the new file and require RED against current main.

### Task 2: Implement ordered cross-reference validation

**File:** Modify `scopeproof_core/schemas/models.py`.

1. Add an after `model_validator` to `ReviewBundle`.
2. Validate identity uniqueness before building lookup maps.
3. Validate finding coverage and evidence ownership.
4. Validate runtime evidence, resolutions, and gate-list criterion references.
5. Repeat the new tests and require GREEN.
6. Run existing schema, gate, reporting, lifecycle, storage, retrieval, and verification suites.
7. Commit the bounded implementation.

### Task 3: Verify the candidate

1. Run Ruff, complete pytest, deterministic benchmark, and `git diff --check main...HEAD`.
2. Build exactly one wheel from `git archive HEAD` and install it with dependencies in a fresh
   virtual environment.
3. Require `pip check`; distribution, module, CLI, web launcher, and new-review provenance all
   equal `0.1.18.dev0`.
4. Run a source-independent probe showing dangling and cross-criterion bundles are rejected while
   a valid round trip succeeds.
5. Re-run the installed benchmark and loopback workbench health check with clean shutdown and no
   traceback.

### Task 4: Integrate and continue

1. Push `codex/review-bundle-integrity` and open one ready PR with reproduced evidence, TDD proof,
   exact verification, and evidence limits.
2. Require all protected checks, squash merge, and verify main CI and CodeQL on the exact merge
   SHA.
3. Fast-forward local main, remove the worktree and branch, reconcile repository hygiene, and
   immediately rotate the persistent goal into the next evidence-backed finite loop.
