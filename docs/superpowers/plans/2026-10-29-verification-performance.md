# Verification Performance Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans for measured coordinator execution,
> followed by independent whole-branch review. Do not optimize before attribution.

**Goal:** Measure the covered-suite bottleneck and close one safe improvement or a no-change finding.

**Architecture:** Complete sequential baseline runs share one locked environment and revision.
Narrow profiles guide one repair; additive timing output leaves all verification gates intact.

**Tech Stack:** Python, pytest, pytest-cov/coverage, uv, Pydantic, protected GitHub CI.

**Spec:** `docs/superpowers/specs/2026-10-29-verification-performance-design.md`

## Global Constraints

- Preserve all tests/assertions, both coverage targets and unrounded 95% floor.
- Preserve five independent lanes, fail-closed verify, CodeQL, package/browser and compatibility checks.
- No evidence-policy shortcuts, source-identity caching by assumption, target-code execution or
  invented human evidence; preserve released bytes, frozen research and dormant Stage 3.
- Stop after one measured repair or a supported no-change result; no standing optimization queue.

## Review Focus

- Local timing comparisons require identical dependencies/test population; hosted differences remain explicit.
- Profiling must account for Streamlit threads rather than mislabel thread waits as the cause.
- Any instrumentation change must retain measured/executable source and covered-line accounting.
- Diagnostics must not alter gate predicates, test selection, environments or failure propagation.
- Required exact-head and resulting-main checks remain engineering evidence only.

### Task 1: Measure and attribute

Files: private external timing logs/data; existing tests remain unchanged.

- [x] Record environment, revision, tracer and hosted baseline step durations.
- [x] Run full covered and bare suites sequentially with per-test durations; confirm matching populations.
- [x] Profile only the primary measured hotspot; decide whether one safe repair is justified.

### Task 2: Implement only the supported change and integrate

Files: `.github/workflows/ci.yml` diagnostics; narrowly justified repair/tests if any;
`docs/audits/2026-10-29-verification-performance.md`; small operating-doc references.

- [x] Add meaningful failing regression for a repair or gate contract, then implement minimally.
- [ ] Compare affected behavior/accounting and timings; run full covered suite at 95%, lint,
  repository contracts and deterministic benchmarks. Do not repeat passing work without new cause.
- [ ] Record version-bound measurements and limitations with validated structured evidence where used.
- [ ] Independent review; fix supported findings and rerun affected checks.
- [ ] PR, reviewed exact-head CI, guarded merge, resulting-main verification, then maintenance.
