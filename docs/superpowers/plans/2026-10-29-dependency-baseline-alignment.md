# Dependency Baseline Alignment Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans for inline implementation and one
> independent whole-branch review. Follow test-driven development for admission regressions.

**Goal:** Make current package declarations enforce the verified maintained runtime baseline.

**Architecture:** Metadata-only runtime correction, preserving all resolved lock versions and
application code. Verify actual admission rules, wheel metadata and isolated resolver behavior.

**Tech Stack:** Python, uv, packaging, Pydantic, pytest, installed-wheel browser and protected CI.

**Spec:** `docs/superpowers/specs/2026-10-29-dependency-baseline-alignment-design.md`

## Global Constraints

- HTTPX `>=0.27,<1`; Pydantic `>=2.13.4,<3`; Streamlit `>=1.66.1,<2`; Pillow `>=13,<14`.
- Preserve resolved versions, optional dependencies, application/core/workflows, frozen R-002.
- Preserve public v0.2.4 bytes/tag/metadata and source identity `0.2.5.dev0`.
- Full suites, unrounded 95% floor, lint, package/browser, compatibility and required gates stay.
- No personal testing, qualifying reviews, publication, deployment, outreach or Stage 3 work.

## Review Focus

- Streamlit's permissive Pillow dependency must not admit an already-installed Pillow 12.x.
- Wheel and installed requirements must exclude old pins, not only source/lock text.
- The four exact floors must resolve together on genuine Python 3.11.
- Historical failed results and released metadata must not be described as repaired in place.
- Verified floors are policy baselines, not proof of every future resolution or earliest support.

### Task 1: Align and verify the distribution contract

- [ ] Replace the old exact-string Streamlit contract with source/lock/installed admission cases;
      watch known older Pydantic/Streamlit and missing Pillow requirements fail.
- [ ] Change declarations; refresh root lock metadata and assert all resolved versions unchanged.
- [ ] Verify the regression passes, build a candidate wheel and inspect its runtime requirements.
- [ ] In a new external Python 3.11 environment, reject old pinned versions, install exact four
      floors together, record identities/versions and require `pip check`.
- [ ] Update current guidance and a dated alignment record; preserve PR #219 observations.
- [ ] Run full isolated floor/source suite, locked covered suite, lint, benchmarks and installed
      browser checks. Obtain independent review, then exact-head CI, guarded merge and main checks.
