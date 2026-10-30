# Git Source Line Coordinates Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans. Root implements the small integrated
> fix; independently authored coordinate regressions and one whole-branch review provide checks.

**Goal:** Make automatic candidate source locations follow Git LF coordinates without changing
frozen research or silently renumbering saved evidence.

**Architecture:** Pure shared LF/CRLF boundary helper used only by production patch parsing and
unchanged-source enumeration. Existing typed evidence/context/export consumes corrected records.

**Tech Stack:** Existing Python/Pydantic/pytest/Git/Playwright; no added dependencies.

**Spec:** `docs/superpowers/specs/2026-10-30-git-source-lines-design.md`

## Global Constraints

- Full source uses LF only and strips one CR only immediately before terminating LF; no phantom
  trailing record. Patch CR normalization uses the following no-final-newline marker because
  GitHub may omit the final protocol LF.
- Preserve embedded CR/VT/FF/FS/GS/RS/NEL/LS/PS and real internal blank/final unterminated lines.
- Frozen R-002 inputs/labels/results/scores and ignored research cache remain untouched.
- No historical reparse/renumber, M3 guard relaxation, schema/policy/dependency/gate change.
- No target execution, human testing, qualifying reviews, release, deployment or outreach.

## Review Focus

- An embedded separator followed by a fake hunk or +/- prefix cannot become diff protocol.
- Removed content cannot become current-head candidate evidence.
- Empty/trailing-newline/CRLF/final-CR cases cannot add or erase source coordinates.
- Candidate/context/export positions agree with independently inspected immutable Git bytes.
- Historical/frozen evidence retains original coordinates, source identity and expectations.

### Task 1: Correct production Git line boundaries

**Files:** New `scopeproof_core/source_lines.py`, `tests/test_source_lines.py`,
`tests/retrieval/test_git_source_coordinates.py`, history regression; modify only
`scopeproof_core/github/client.py`, `scopeproof_core/retrieval/engine.py` and relevant current
documentation/Windows targeted test configuration. Leave all frozen research untouched.

**Interfaces:** `split_git_source_lines(text: str, *, strip_crlf: bool = True) -> list[str]`; use it from `_parse_patch`
and `_candidate_file`. No other public/core model signature changes.
Patch parsing retains raw CR until checking the following no-final-newline marker; protocol LF
must not erase a real final source CR; absent a marker, normalize CRLF even when GitHub omits
the final protocol LF.

- [ ] Write and observe failing independent parser/retrieval coordinate and helper boundary tests.
- [ ] Implement the small helper and two call sites; run targeted sources/context/history/export
      tests. Preserve all unchanged LF/CRLF cases and removed-line exclusions.
- [ ] Record frozen-file hashes, constructed results and current guidance; run complete coverage,
      lint/lock/benchmarks, installed-wheel browser and available compatibility checks.
- [ ] Obtain independent whole-branch review; verify supported fixes RED→GREEN; open a PR and
      merge only after final-head CI and review findings are resolved.
- [ ] Verify resulting main and clean sync, retain failed/passing evidence separately and archive
      this task's owned execution ledger before closing the goal.
