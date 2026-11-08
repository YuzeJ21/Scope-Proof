# Saved-history event validation plan

> **For agentic workers:** Execute this bounded slice inline, then obtain fresh independent engineering review.

**Goal:** Remove reproduced repeated whole-event scans when validating retained analyses, without changing accepted states, serialized output or rejection rules.

**Architecture:** After Pydantic reconstructs the state, group its resolution events once by explicit criteria revision, preserving list order. Feed the matching slices to the existing projection helpers; retain every deterministic gate, evidence and temporal-integrity check. The index lives only within one validation call.

**Tech stack:** Python 3.11+, Pydantic, pytest, existing cross-platform and installed-wheel CI.

## Design and measured trigger

New constructed inputs, separate from all frozen/native fixtures, cover 1–500 retained analyses and 4–128 events per revision below the unchanged 64 MiB cap. On clean main c749917, the largest input contains 500 historical analyses and 64,128 events in 45,422,705 bytes. A causal probe measured 64,256,256 event elements passed to projection helpers during one validation. The helpers consumed 3.349 of 4.217 seconds. An ordered partition replay retained all other validation and produced identical full state JSON in 0.690 seconds. This justifies a local algorithm change, not a cache, schema/storage rewrite or latency guarantee.

## Global constraints and review focus

- Rebuild with Pydantic before grouping; retain all gates, evidence rules, temporal checks and error order.
- Preserve list order, explicit revision arguments, unknown-history semantics and unmatched-event rejection. Do not infer ownership for unknown history.
- No cross-call cache, skipped validation, truncation, cap change, public API or producer/version change.
- Keep AGENTS.md, frozen R-002, native/released corpus bytes and public artifacts unchanged. Constructed actors are not human evidence.
- No release, Pages deployment, outreach, personal testing, qualifying reviews or Stage 3 claim.
- Test mixed/interleaved revisions, final acceptance/revocation, missing events, unknown history and dangling events; preserve existing manual-evidence and premature-acceptance rejection tests.

## Task 1 — Bound event projection work

- [x] Add a small real-state regression that instruments unchanged helpers and fails on repeated whole-history scans, without a wall-clock threshold.
- [x] Add semantic/no-mutation tests for interleaved revisions, empty revision, acceptance/revocation, unknown history and unmatched events.
- [x] Build the ordered index in `scopeproof_core/gates/validation.py`; pass revision slices to unchanged helpers and retain the temporal checker verbatim.
- [x] Run focused gate/storage/lifecycle regressions and lint. Repeat the same immutable-input operation matrix against the actual production change; preserve original results separately.

## Task 2 — Verify and integrate

- [x] Record method, input identities, measured results and limitations; update the roadmap only for this reproduced constraint.
- [ ] Obtain independent whole-branch engineering review and resolve supported findings.
- [ ] Require exact-head CI, full suite and unrounded 95% coverage, deterministic benchmarks, installed CLI/browser journeys, Python and Windows lanes.
- [ ] Merge the reviewed exact head; verify resulting main CI and clean synchronized checkouts. Public v0.2.6 and Pages remain unchanged.
