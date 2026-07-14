# Runtime-Evidence Required Labels Design

## Problem

The continuation objective identifies the manual runtime-evidence form and final-acceptance
boundary as the next first-use investigation. Current `main` no longer reproduces the original
readiness defect: empty required values keep `Save manual runtime evidence` disabled, unexpected
Pydantic failures use stable product copy, and the final-acceptance boundary states that acceptance
does not resolve criteria or override the deterministic gate.

A current source-bound browser audit found a narrower accessibility and recovery gap. The five
required controls are labeled `Artifact or URL`, `Runtime scenario`, `Environment`, `Observed
result`, and `Runtime reviewer`; the optional control is labeled `Runtime limitations`. None of
the six inputs exposes a native `required` attribute, `aria-required`, or an associated
`aria-describedby` reference. Requiredness is explained only in a later caption after all inputs
and the evidence-level selector. A reviewer therefore cannot determine required versus optional
status from the field labels themselves, and assistive technology receives no requiredness signal
while moving input by input.

The accepted audit screenshots are stored at:

- `/tmp/scopeproof-runtime-acceptance-audit-2026-07-14/01-current-runtime-prerequisites.png`
- `/tmp/scopeproof-runtime-acceptance-audit-2026-07-14/02-current-final-acceptance-boundary.png`

The local demo is controlled product evidence only. It is not runtime evidence for a pull request,
external adoption evidence, or final acceptance.

## Intended Outcome

Keep the existing form order and behavior. Make requiredness part of every runtime input's visible
and accessible label:

- `Artifact or URL (required)`
- `Runtime scenario (required)`
- `Environment (required)`
- `Observed result (required)`
- `Runtime reviewer (required)`
- `Runtime limitations (optional)`

Keep the existing summary caption that names all five required values, explains E3 and E4, states
that saving does not resolve the criterion or record final acceptance, and says limitations are
optional. This deliberate repetition provides both per-control context and a concise submission
contract immediately before the Save action.

## Approaches Considered

### 1. Add required or optional text to the existing labels — selected

This uses Streamlit's supported label interface, follows the current workbench visual language,
keeps the visible and accessible name aligned, and requires no custom markup or dependency. The
stable widget keys remain unchanged, so saved session behavior and AppTest selectors continue to
work.

### 2. Add one help tooltip to each field

Tooltips would repeat more copy, require six extra interactions, and make requiredness dependent on
hover or explicit help activation. They would not improve the default field name announced during
sequential navigation.

### 3. Inject custom HTML or JavaScript to set `aria-required`

This could expose a native ARIA state, but it would couple ScopeProof to Streamlit's generated DOM,
add a fragile presentation layer, and conflict with the current component pattern. Label text is a
stable, supported, dependency-free improvement with equivalent user-visible meaning.

## Architecture and Data Flow

Only `apps/web/app.py` changes in production. Each existing Streamlit input receives updated label
text while retaining its current `key`, value, type, order, and validation path.

The data flow is unchanged:

1. Streamlit collects human-supplied input under the existing session-state keys.
2. The existing readiness Boolean requires non-whitespace text in the same five values.
3. `RuntimeEvidence` remains the authoritative Pydantic boundary.
4. `append_runtime_evidence` remains the only runtime-record mutation path.
5. Static findings, criterion resolutions, final acceptance, gate evaluation, exports, and storage
   remain unchanged.

## Safety and Error Behavior

- Empty or whitespace-only required inputs continue to disable Save.
- Complete required inputs continue to enable Save.
- Unexpected model or lifecycle failures continue to use the existing stable recovery copy.
- Limitations remain optional, but any persisted limitation item still passes through the existing
  Pydantic validation boundary.
- No PR code executes and no runtime result, reviewer identity, acceptance, or evidence is inferred.
- No network request, paid service, API, LLM, telemetry, dependency, private repository, fork, or
  external write is introduced.

## Regression Coverage

Add a focused Streamlit AppTest that reaches the analyzed demo and requires the exact six labels.
The test must also prove that the five required labels map to the existing stable widget keys, the
optional label maps to `runtime_limitations`, the empty Save action remains disabled, and the final
acceptance boundary copy remains unchanged.

Preserve the existing tests that prove:

- whitespace-only required values keep Save disabled;
- all five complete values enable Save;
- a controlled in-memory save clears the form and prevents an accidental repeat;
- runtime evidence does not change static findings;
- final acceptance remains independently recordable and cannot override blocker precedence.

Verification must include focused AppTests, Ruff, the complete offline suite, the deterministic
12-case benchmark, `git diff --check`, clean-wheel installation, installed benchmark, exact local
workbench health, and a source-bound browser comparison. Browser verification must not submit a
runtime record, criterion resolution, or final acceptance.

## Accessibility Evidence Limits

DOM inspection can prove the updated accessible names and screenshot inspection can prove visible
labels, reading order, disabled state, and boundary copy. Those checks do not prove complete WCAG
conformance, screen-reader announcement quality, keyboard focus order, zoom behavior, or platform-
specific high-contrast behavior.

## Out of Scope

- Adding new fields, placeholders, examples, or evidence requirements.
- Changing `RuntimeEvidence`, evidence levels, lifecycle services, schemas, or record versions.
- Gating first final acceptance on criterion resolutions or a Ready verdict.
- Changing findings, resolutions, final acceptance, gate precedence, exports, or persistence.
- Submitting demo values as genuine runtime evidence.
- Publishing a release for this presentation-only improvement.
