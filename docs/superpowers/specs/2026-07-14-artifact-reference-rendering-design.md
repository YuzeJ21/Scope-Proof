# Artifact-Reference Rendering Design

## Problem

`RuntimeEvidence.artifact_reference` intentionally accepts any nonblank human-supplied reference.
The workbench labels the field `Artifact or URL`, and the schema regression suite already accepts
`artifact-42`. The display layers do not preserve that distinction:

- `apps/web/app.py` always emits a Markdown link;
- `export_markdown()` always emits a Markdown link; and
- `export_html()` always emits an HTML anchor.

A deterministic probe against `main` at
`826a57accaa2460cec899337a27a8cc1ff41d673` rendered `artifact-42` as a relative link and rendered
`javascript:alert(1)` as a clickable HTML `href`. The latter is escaped as attribute text but the
scheme remains active. This turns a valid artifact identifier into misleading navigation and makes
an untrusted non-web scheme clickable in the self-contained HTML report.

A fresh source-bound browser audit confirmed the current form contract and saved
`/tmp/scopeproof-artifact-reference-audit-2026-07-14/03-current-main-artifact-or-url-label.png`.
No runtime evidence, resolution, final acceptance, or saved review was created. An earlier capture
was rejected after environment tracing proved that the console entry point still loaded a stale
`0.1.15.dev0` site-packages copy. The local environment was repaired with the current editable
`0.1.18.dev0` source before the accepted audit.

## Intended Outcome

Preserve the existing `Artifact or URL` model and stored value exactly.

- A valid absolute HTTP or HTTPS URL is clickable in Streamlit, Markdown, and HTML.
- Every other nonblank reference, including artifact IDs, local paths, relative references, and
  non-web schemes, is rendered as plain text.
- JSON and CSV continue exporting the exact validated value without presentation markup.
- The helper rejects link treatment when the value contains whitespace, angle brackets, lacks a
  network location, or uses any scheme other than HTTP or HTTPS.

This is presentation safety, not evidence validation. A non-link artifact reference remains valid
runtime evidence when the rest of the Pydantic contract is satisfied.

## Approaches Considered

### 1. Link only validated HTTP(S) references — selected

One core reporting helper classifies linkable references and creates the Markdown fragment used by
both the workbench and Markdown export. HTML uses the same classifier before producing an escaped
anchor. This retains useful navigation for real web artifacts while keeping every other supported
reference truthful and inert.

### 2. Require every artifact reference to be an HTTP URL

This would simplify rendering but contradict the field label, existing schema behavior, and valid
artifact identifiers such as `artifact-42`. It would also be a persisted-object compatibility
change without evidence that URLs are always available.

### 3. Render every artifact reference as plain text

This would remove navigation risk but unnecessarily degrade valid HTTPS evidence links. The
product already uses immutable, clickable web evidence where a real URL is available.

## Architecture

Create `scopeproof_core/reporting/references.py` with two small interfaces:

```python
def is_linkable_artifact_reference(value: str) -> bool: ...
def render_artifact_reference_markdown(value: str) -> str: ...
```

`is_linkable_artifact_reference()` uses `urllib.parse.urlsplit`, permits only case-insensitive
`http` and `https`, requires a nonempty network location, and rejects whitespace plus `<` or `>`.
It does not normalize, trim, or rewrite the stored evidence value.

`render_artifact_reference_markdown()` escapes Markdown text. For linkable values it returns a
label linked to an angle-bracket destination; otherwise it returns escaped plain text.

`apps/web/app.py` and `export_markdown()` consume the Markdown helper. `export_html()` consumes the
classifier and keeps using `html.escape()` for both label and attribute output. CSV and JSON are
unchanged.

## Data Flow and Boundaries

1. A human supplies the runtime artifact reference.
2. `RuntimeEvidence` continues validating that it is nonblank and otherwise preserves it exactly.
3. Persistence, JSON, and CSV retain the exact value.
4. Presentation code classifies the value only when creating clickable output.
5. Runtime evidence still does not alter static findings, criterion resolution, final acceptance,
   or the deterministic gate.

The core remains independent from Streamlit and GitHub UI layers. No PR code executes, and no
network request, dependency, paid API, billing, telemetry, or external write is introduced.

## Regression Coverage

Test-first coverage must prove:

- HTTPS and HTTP values are classified as linkable;
- artifact identifiers, relative paths, `file:`, `javascript:`, missing-host URLs, whitespace, and
  angle-bracket values are not linkable;
- Markdown rendering escapes label syntax and links only safe HTTP(S) values;
- Markdown and HTML exports render artifact IDs and unsafe schemes as plain text without `href`;
- Markdown and HTML exports retain clickable, escaped HTTPS links;
- Streamlit AppTest renders an artifact ID as plain text after a controlled in-memory fixture save;
- the stored `RuntimeEvidence.artifact_reference`, JSON, and CSV values remain unchanged.

Run focused tests, all Streamlit and reporting tests, Ruff, the complete offline suite, the 12-case
deterministic benchmark, `git diff --check`, clean-wheel identity/dependency/benchmark/health
checks, and a source-bound browser audit that does not submit invented runtime evidence.

## Out of Scope

- Changing `RuntimeEvidence`, its persisted format, or accepted reference values.
- Fetching, probing, validating ownership of, or executing any artifact URL.
- Rewriting existing review files or trimming reference text.
- Broad Markdown sanitization unrelated to runtime artifact references.
- Generic security scanning, auto-fix, paid services, APIs, fork testing, or a release.
