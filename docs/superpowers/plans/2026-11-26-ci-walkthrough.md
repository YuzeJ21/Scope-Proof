# Offline CI walkthrough implementation plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan in this session.

**Goal:** Deliver one reproducible no-install walkthrough of the existing two-build CI handoff.

**Architecture:** A presentation recipe reads the existing private candidate's exact
snapshots and constructed inputs. It validates their original producer, adds a
labelled presentation, and packages provenance and unchanged inputs. Core behavior
and the original private candidate stay unchanged.

**Tech Stack:** Python 3.12, existing Pydantic models/exporters, stdlib HTML/ZIP, pytest, Chromium.

**Spec:** `docs/superpowers/specs/2026-11-26-ci-walkthrough-design.md`

## Global constraints

- Preserve deterministic gates, saved reviews, and implementation/test/runtime separation.
- Validate every persisted/exported object with Pydantic; execute no target repository code.
- Preserve frozen R-002 and the v0.2.6 example. No package or website publication.
- Development remains unpublished `0.2.9.dev0`; published evaluation remains v0.2.8.

## Review focus

- A passing CI result must never imply human acceptance or runtime verification.
- The targeted rerun must retain Build B's SHA and unchanged review bytes.
- A supplied wheel must match the installed producer, rather than merely its version.
- Missing, mismatched or pending input must not leave a plausible completed walkthrough.
- Offline links and narrow-screen tables must remain usable with no automatic remote requests.

### Task 1: Validated reproducible builder

**Files:** Create `scripts/build_ci_walkthrough.py`, `tests/test_ci_walkthrough.py`.

**Interfaces:** `build_walkthrough(source: Path, output: Path) -> WalkthroughManifest`;
`WalkthroughManifest` records producer, scenario steps, and artifact digests.

- [x] Write tests for three exact-build states, unchanged input bytes, deterministic
  archive generation, refusal of existing output/mismatches, and false evidence credit.
- [x] Run the new tests and observe their failure before implementing the builder.
- [x] Implement with existing `JsonReviewStore`, `CIStatusManifest`, CI projection,
  and presentation labels. Keep original snapshot bytes beneath one disclosure.
- [x] Run `.venv/bin/python -m pytest -q tests/test_ci_walkthrough.py` and Ruff.

### Task 2: Installed generation, offline reading, and current entry points

**Files:** Create `docs/examples/ci-handoff/` and its guide; modify `README.md`,
`docs/README.md`, `docs/evaluation-guide.md`, `ROADMAP.md`, and `CHANGELOG.md`.

**Interfaces:** Consumes the builder and manifest from Task 1; produces a downloadable
labelled ZIP with an index and three linked exact-build snapshots.

- [x] Reuse the discovered candidate's exact reports and inputs; verify its recorded
  wheel against original Git source without rebuilding the completed candidate.
- [x] Verify two generations are identical and existing review/manifests unchanged.
- [ ] Add/run offline Chromium checks for all pages, local links, phone/desktop
  overflow, and zero automatic external requests.
- [ ] Run focused regressions and the normal source suite; record actual results.
- [x] Update current docs around the completed deliverable and its bounded maturity.
- [x] Obtain one independent whole-change review and fix material findings.
- [ ] Sync a reviewable branch/PR via GitHub; do not release or deploy.
