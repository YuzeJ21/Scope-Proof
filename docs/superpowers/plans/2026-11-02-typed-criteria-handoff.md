# Typed criteria handoff implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan. Steps use checkbox syntax for tracking.

**Goal:** Preserve explicitly confirmed complete normalized criteria in an automated review handoff.

**Architecture:** Add one pure-core Pydantic document; keep bounded file reading and command wiring
in the CLI. Reuse current confirmation digests, analysis, saved validation and atomic output.

**Tech Stack:** Python 3.11+, Pydantic 2, argparse, pytest, existing package/browser CI.

**Spec:** `docs/superpowers/specs/2026-11-02-typed-criteria-handoff-design.md`

## Global constraints

- No new dependency, changed evidence/gate policy, schema migration, or frozen benchmark edit.
- Optional normalized document maximum 1 MiB; schema version 1; nonempty unique criterion IDs.
- Exact UTF-8 source and complete ordered normalized criteria must match explicit confirmation.
- Source version 0.2.5 and saved record version 9; no publication, deployment or Stage 3 advance.
- No personal testing, qualifying reviews, authenticated actor claims or target code execution.

## Review focus

1. Edited normalized text differs from the source; preserve explicit intent without guessing mapping.
2. Dropping the typed option must never accept a custom confirmation with weaker defaults.
3. Invalid input must fail before fetch/fixture ingestion and before any report/store writes.
4. Windows CRLF, non-ASCII source and full-field order must survive identical digest checks.
5. A draft is not confirmation, actor authentication, or a runtime/test evidence record.

## File structure

- Create `scopeproof_core/criteria/document.py`: pure validated source-bound document.
- Modify `scopeproof_core/cli.py`: shared optional typed input, draft command, atomic confirmation.
- Create `tests/cli/test_criteria_document.py`: commands, field preservation, failure boundaries.
- Create `tests/cli/test_installed_criteria_document.py`: isolated packaged public command journey.
- Modify `.github/workflows/ci.yml`: execute new installed CLI case and Windows focused checks.
- Update README, ROADMAP, current release-status and positioning; add dated market/audit records.

### Task 1: Complete criteria handoff with product direction and integration

**Files:** All files in the file structure above.

**Interfaces:**
- Consumes existing `Criterion`, source/normalized digest helpers, criteria provenance,
  `_read_bounded_regular_file`, `_build_bundle`, `JsonReviewStore`, and atomic output.
- Produces `NormalizedCriteriaDocument` with `criteria_for_source(source_text: str) -> list[Criterion]`;
  `prepare-criteria` and optional `--criteria` on the three existing public commands.

- [ ] Write `test_prepare_criteria_emits_unconfirmed_complete_draft` and
  `test_typed_handoff_preserves_complete_criteria_in_saved_review`; assert exact source hash,
  absent confirmation, all fields, `AC-20`/`AC-03`, E3/E4 and should-have priority/order.
- [ ] Run those tests on unchanged product source; expect missing-command/option failures.
- [ ] Add the core model, one shared CLI input helper and command wiring; preserve default parser.
- [ ] Add malformed/empty/duplicate/extra/oversized rejection and each-field/order/source mutation
  cases; verify no fetch/fixture access/report/store writes. Test omitted typed input with a
  custom confirmation fails, no-overwrite publication, edited normalized text, and legacy hashes.
- [ ] Run focused tests and repository contracts; expect all pass.
- [ ] Add the outside-checkout installed journey and Windows/engineering CI invocation.
- [ ] Refresh dated market evidence, positioning, roadmap next-stage decision and source-only docs.
- [ ] Run `python -m pytest --cov=scopeproof_core --cov=apps --cov-fail-under=95 -q` and enforce
  unrounded coverage >=95; expect zero failures. Run Ruff, lock check, both deterministic benchmarks,
  frozen-input comparison, clean wheel install/pip check, installed CLI and packaged-browser suite.
- [ ] Commit; obtain one fresh independent whole-branch review. Resolve supported material findings
  by RED→GREEN regressions/full suite; preserve review and dispositions in the external audit packet.
- [ ] Prepare PR, require exact-head CI and resolved findings, merge with expected-head binding,
  verify resulting main CI/clean synchronized checkouts and version-bound artifact identity.
- [ ] Run read-only packet completion assertions; archive the owned execution ledger and report
  exact commits, results, product limits and the next evidence/authorization gates.

**Completion command:** external packet `complete-check.py` validates the final integration evidence;
it must report all assertions passed before this task is marked complete.
