# Candidate Evidence Context Guard Implementation Plan

**Goal:** Prevent whitespace-only candidate-evidence identity, context, and limitations from being
persisted or exported as explicit evidence, while starting the v0.1.18 development line.

**Architecture:** Keep retrieval and gate logic unchanged. Enforce the invariant in the
UI-independent `EvidenceItem` Pydantic schema, cover the boundary with regression-first tests, and
verify the source and installed wheel before protected integration.

## Constraints

- Preserve valid text exactly; do not strip evidence fields.
- Keep an empty limitations list valid.
- Do not change gate precedence, evidence levels, URL/SHA semantics, repository permissions, or UI.
- Do not create issue comments, reviewer requests, releases, fork tests, or notification-only work.

### Task 1: Lock the schema defect with failing tests

**Files:**
- Modify: `tests/schemas/test_models.py`
- Modify: `tests/test_repository_contracts.py`

1. Add a reusable valid `EvidenceItem` payload.
2. Parameterize all required string fields over `""`, `"   "`, and `"\t\n"`; require
   `ValidationError`.
3. Parameterize blank limitation members and require `ValidationError`.
4. Require valid surrounding whitespace to be preserved and an empty limitations list to remain
   valid.
5. Change the single-version-source assertion to `0.1.18.dev0`.
6. Run only the new schema tests and version contract; require RED against the v0.1.17 source.

### Task 2: Implement the Pydantic invariant

**Files:**
- Modify: `scopeproof_core/schemas/models.py`
- Modify: `scopeproof_core/version.py`

1. Add a field validator for the eight required candidate-evidence string fields.
2. Add a limitations-list validator.
3. Advance `__version__` to `0.1.18.dev0`.
4. Repeat the focused tests and require GREEN.
5. Run the existing schema, exporter, storage, retrieval, and repository-contract suites.
6. Commit the bounded implementation.

### Task 3: Verify the candidate

1. Run Ruff, complete pytest, deterministic benchmark, and `git diff --check main...HEAD`.
2. Build exactly one wheel from `git archive HEAD` in a fresh temporary directory.
3. Install it with declared dependencies into a fresh virtual environment.
4. Require `pip check`; distribution, module, CLI, web launcher, and new-review provenance all
   equal `0.1.18.dev0`.
5. Re-run the installed benchmark and loopback workbench health check with clean shutdown and no
   traceback.
6. Run a source-independent probe proving blank fields and limitations are rejected, valid values
   are preserved, and empty limitations remain accepted.

### Task 4: Integrate and continue

1. Push `codex/candidate-evidence-context-guard`.
2. Open one ready PR with reproduced evidence, TDD results, exact verification, and evidence limits.
3. Require all protected checks, squash merge, and verify CI and CodeQL on the exact merge SHA.
4. Fast-forward local main, remove the worktree and branch, reconcile public repository hygiene,
   and immediately rotate the persistent goal to the next evidence-backed gap.
