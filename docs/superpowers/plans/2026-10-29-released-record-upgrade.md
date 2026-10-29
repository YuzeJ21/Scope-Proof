# Published-record Upgrade Rehearsal Implementation Plan

> **For agentic workers:** Execute with a scoped old-writer recipe implementer and independent
> whole-branch review. The coordinator owns package verification, reader checks and integration.

**Goal:** Establish actual v0.2.3 writer → v0.2.4 reader compatibility for one constructed history,
then retain its native bytes as an offline regression without inventing acceptance or user evidence.

**Architecture:** Public packages run only in isolated external environments. A version-guarded
recipe uses old supported APIs; native record bytes remain unchanged. Current tests load the
committed old-producer fixture, validate its provenance and assert preserved/conservative behavior.

**Tech Stack:** Python, Pydantic, pytest, uv, public wheels, JSON, Markdown, protected GitHub CI.

**Spec:** `docs/superpowers/specs/2026-10-29-released-record-upgrade-design.md`

## Global Constraints

- Preserve published assets, frozen R-002 inputs/results, explicit criteria/reviewer decisions.
- All new actors and runtime records are constructed automation with zero human-use credit.
- Never execute target-repository code; no live PR or app-server ingestion is needed.
- No publishing/deployment/outreach/Stage 3 work; merge only the reviewed passing exact head.
- Original old-writer bytes are immutable; migration/resave occurs on disposable copies.

## Review Focus

- Native v4 linked runtime records must not undergo v1/v2 unlinking.
- Criteria revisions and historical events must retain identities/provenance and timestamps.
- Unknown newer metadata must remain unknown and historical acceptance cannot hide scope gaps.
- Public-reader results must stay distinct from later development-reader regression/fixes.
- The generated record and actor labels must not imply genuine human or target-runtime evidence.

### Task 1: Run the released-package rehearsal

Files: external private work directory and
`tests/fixtures/released_v023_upgrade/generate_record.py`.

- [x] Verify public wheel digests/tags/core bytes and install both trusted wheels externally.
- [x] Generate one native v4 two-revision record with the old writer; save/reload old state.
- [x] Preserve original bytes; load twice/export/resave/reopen using published v0.2.4.
- [x] Check preserved facts, conservative unknowns/gates and nonmutating head detection.
- [x] Record Pydantic-validated provenance/results with accurate actor and version boundaries.

### Task 2: Retain the native-producer regression and review

Files: `tests/fixtures/released_v023_upgrade/native_v4.json`, `provenance.json`,
`tests/storage/test_released_v023_upgrade.py`, `docs/research/2026-10-29-v023-v024-upgrade.md`,
small links in `ROADMAP.md`, `docs/README.md`, and `CHANGELOG.md`.

- [x] Add native-producer fixture assertions; observe failure before fixture import.
- [x] Retain exact original JSON and validate provenance; add only narrowly supported fixes if needed.
- [x] Run migration/storage/schema checks, lint, locked checks and deterministic benchmarks.
- [ ] Independent whole-branch review, resolve supported findings and rerun affected checks.
- [ ] Commit/push PR; require full-suite/95% coverage, compatibility, packaging/browser and CodeQL.
- [ ] Merge expected reviewed head, verify resulting main and unchanged release/research, then stop.
