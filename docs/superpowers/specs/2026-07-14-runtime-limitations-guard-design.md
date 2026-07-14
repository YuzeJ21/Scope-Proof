# Runtime-Evidence Limitations Guard Design

## Verified defect

Current `main` correctly prevents blank required runtime-evidence fields in Streamlit and rejects them in the Pydantic model. The optional `limitations` list has no equivalent item validation. A deterministic source probe constructed and serialized `RuntimeEvidence(limitations=["   "])`, and the Markdown exporter rendered that value as an empty `Limitations:` line.

This is a persisted-object integrity gap. A limitation is optional, but an entry that is present must contain usable human-supplied context.

## Intended outcome

- Reject a `limitations` list when any item contains only whitespace.
- Preserve valid limitation strings exactly, including intentional surrounding whitespace.
- Preserve an omitted or empty limitations list as valid.
- Keep Streamlit's existing blank-line filtering and all runtime-evidence, resolution, final-acceptance, and gate semantics unchanged.

## Approaches considered

### 1. Explicit Pydantic list-item validator — selected

Add a `field_validator("limitations")` to `RuntimeEvidence`. Reject the list when any item has an empty `strip()` result, and otherwise return the original list unchanged. This places the rule at the authoritative persisted/exported-object boundary and matches the existing nonblank required-context validator.

### 2. Filter blank limitations in Streamlit or exporters

The current UI already drops blank lines, but other constructors, imported records, and future callers can bypass it. Export-time filtering would silently mutate invalid evidence and leave JSON or local storage inconsistent with Markdown.

### 3. Enable global string stripping

Global normalization would alter valid human-supplied text across the model and is broader than the reproduced defect.

## Architecture and data flow

Only the core Pydantic model and focused schema tests change. `RuntimeEvidence` remains independent from Streamlit and GitHub layers. Existing persistence, lifecycle, and exporters continue consuming the validated model without additional filtering.

## Error and safety behavior

- Whitespace-only limitation items raise a stable Pydantic validation error.
- Valid values are not trimmed or rewritten.
- No evidence is inferred, upgraded, or removed.
- Runtime evidence remains append-only and cannot change static findings, criterion resolutions, final acceptance, or the deterministic gate.
- No untrusted repository code executes and no external validation claim is created.

## Verification

- Add a failing schema regression for whitespace-only limitation items.
- Add a preservation regression for a valid limitation with surrounding whitespace.
- Preserve omitted and empty-list behavior.
- Run focused schema and exporter tests, Ruff, the complete offline suite, deterministic benchmark, and `git diff --check`.
- Build a clean archived wheel and run an installed-package schema probe plus benchmark.
- Publish through protected checks and verify CI and CodeQL on the exact merge SHA.

## Out of scope

- Changing required runtime-evidence fields, criterion references, evidence levels, record versions, UI copy, exporters, lifecycle, gate evaluation, or final acceptance.
- Silently normalizing evidence text.
- Releases, comments, fork testing, paid services, APIs, telemetry, or synthetic external evidence.

## Evidence limits

The source probe and regression tests prove deterministic schema and export behavior for controlled local records. They do not prove external adoption, a real PR runtime result, or reviewer acceptance.
