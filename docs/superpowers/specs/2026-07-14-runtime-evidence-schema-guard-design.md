# Runtime-Evidence Schema Guard Design

## Context

The current goal identified an earlier Streamlit defect in which blank manual runtime-evidence fields could reach Pydantic and expose raw validation output. Current `main` no longer reproduces that presentation defect: commit `81c689d` disables `Save manual runtime evidence` until all five required inputs contain non-whitespace text and translates fallback failures into stable recovery copy.

A current combined flow audit at `798b73817a6296d163d2b6e329329c04ba90fde6` confirmed:

- blank and whitespace-only form input keeps the save action disabled;
- the required-field caption is visible;
- runtime evidence remains append-only and does not change static findings or the gate;
- final acceptance is an independent review-level event and does not override a Blocked gate.

Audit evidence is stored under `/Users/yjian070/.codex/visualizations/2026/07/14/scopeproof-runtime-evidence-audit/`.

The audit found a remaining defense-in-depth gap. `RuntimeEvidence` uses `Field(min_length=1)` for `artifact_reference`, `scenario`, `environment`, `result`, and `reviewer`. Pydantic therefore accepts strings containing only whitespace when the model is constructed outside Streamlit. A deterministic source probe successfully serialized a record whose five required human-supplied fields were each three spaces.

## Goal

Make the Pydantic schema reject whitespace-only required runtime-evidence fields so persisted, imported, and future non-UI records cannot bypass the prerequisite enforced by Streamlit.

## Approaches considered

### 1. Explicit nonblank field validator — selected

Add one `field_validator` covering the five required human-supplied text fields. Reject a value when `value.strip()` is empty, but return a valid value unchanged.

This closes the integrity gap without silently rewriting evidence text. It also keeps validation owned by the Pydantic model that governs persisted and exported objects.

### 2. Enable global string stripping for `RuntimeEvidence`

`ConfigDict(str_strip_whitespace=True)` would allow the existing `min_length=1` constraints to reject blank values. It would also normalize every string in the model, including surrounding whitespace and potentially list entries. That is broader than the observed defect and would silently alter valid human-supplied evidence.

### 3. Keep UI-only validation

The existing Streamlit readiness check prevents the interactive path from submitting whitespace. It does not protect model construction, import, reopening, or future callers. This fails the defense-in-depth and persisted-object validation requirement.

## Product and domain behavior

- `RuntimeEvidence` rejects whitespace-only `artifact_reference`, `scenario`, `environment`, `result`, and `reviewer` values.
- Valid nonblank values are preserved exactly; the schema does not trim or rewrite evidence.
- Existing `min_length=1`, `extra="forbid"`, and E3/E4 validation remain in force.
- The Streamlit disabled state, prerequisite caption, stable fallback error, reset-after-save behavior, and success copy remain unchanged.
- Runtime evidence remains append-only and cannot upgrade static findings, resolve a criterion, record final acceptance, or change the deterministic gate.
- Final acceptance remains independently recordable and cannot override blocker precedence.

## Architecture

Only `scopeproof_core/schemas/models.py` and focused schema regression tests change. The validator stays in the core Pydantic model, independent from Streamlit and GitHub presentation layers.

No new schema field, persisted format, migration, dependency, session key, workflow, API, or service is introduced. Existing valid records remain compatible because their values already contain non-whitespace text.

## Error and safety behavior

- Direct Pydantic construction with a whitespace-only required field raises `ValidationError` with a stable `must contain non-whitespace text` validation message.
- Streamlit continues to prevent the invalid submission before model construction and retains its generic recovery message as defense in depth.
- No raw validation output is added to user-facing surfaces.
- No untrusted code executes and no runtime result is inferred.

## Regression coverage

- Parameterize the five required fields and prove each rejects a whitespace-only value.
- Prove a valid value with surrounding whitespace remains unchanged, making the no-normalization decision explicit.
- Preserve the existing E3/E4 restriction and complete-context happy path.
- Run focused schema and lifecycle tests, Ruff, the full offline suite, deterministic benchmark, and diff checks.
- Build and clean-install one wheel; run a direct installed-package schema probe, then verify version identity, dependency consistency, benchmark, and exact web health.
- Recheck the packaged manual-evidence form and final-acceptance boundary without recording invented external evidence.

## Out of scope

- Changing Streamlit labels, layout, readiness logic, or recovery copy.
- Normalizing or trimming valid runtime-evidence strings.
- Changing criterion findings, human resolutions, final acceptance, gates, exports, or record versions.
- Adding APIs, paid services, billing, telemetry, forks, external validation, or notification-only GitHub activity.

## Evidence limits

The local demo and schema probes establish deterministic product behavior for the controlled path. They do not represent external runtime evidence, real user adoption, or acceptance of a public pull request.
