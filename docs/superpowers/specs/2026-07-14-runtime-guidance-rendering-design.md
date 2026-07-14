# Runtime Guidance Rendering Design

## Problem

The runtime-evidence and final-review boundary copy exists in `apps/web/app.py` and is visible to
Streamlit AppTest, but a fresh installed workbench session does not render every item. A live browser
reproduction on `main` at `400b09c` showed three omissions after loading the deliberately
constructed demo, confirming criteria, and running deterministic analysis:

- the criterion receiving the manual runtime record;
- the E3/E4 meaning and non-resolution boundary;
- the `Criterion resolution` heading and its criterion/final-acceptance boundary.

The browser still showed the observation disclaimer, required-field copy, controls, disabled empty
save action, and final-review acceptance boundary. Restarting the server and repeating the flow
produced the same result. The current AppTests pass because they inspect Streamlit's element model,
not the browser's reconciled presentation.

## Intended Outcome

Keep the same workflow, text, schemas, widgets, values, and deterministic behavior while making each
context boundary an atomic presentation block:

1. One caption below `Manual runtime evidence` states both the selected criterion target and the
   human-supplied-observation boundary.
2. One caption below `Runtime evidence level` states the E3/E4 meanings, the non-resolution and
   non-acceptance boundary, required fields, and optional limitations.
3. One Markdown block presents the `Criterion resolution` heading together with its selected
   criterion and final-acceptance boundary.

Atomic blocks remove the consecutive text elements that disappear in the live workbench while
preserving the existing visual language and reading order.

## Approaches Considered

### 1. Consolidate related guidance into atomic blocks — selected

This is presentation-only, uses existing Streamlit primitives, adds no dependency, and makes the
boundary text inseparable from its section or control. It is the smallest change that directly
addresses the reproduced browser result.

### 2. Add a browser automation dependency and permanent end-to-end suite

This could detect frontend reconciliation in CI, but it expands installation and CI complexity for
a bounded copy-layout defect. The current product already uses real-browser acceptance checks for
reviewed UI slices; a separate testing-infrastructure decision can be made if the pattern recurs.

### 3. Upgrade or pin Streamlit

The repository has no evidence that a dependency version change fixes this exact presentation
behavior. Upgrading would broaden the change surface and could introduce unrelated widget or
AppTest changes.

## Architecture and Safety

Only `apps/web/app.py` and its Streamlit AppTests change. No Pydantic model, persisted object,
exporter, lifecycle operation, finding, gate, or final-acceptance rule changes. Runtime evidence
remains human supplied and append-only. The workbench still does not execute PR code, infer runtime
results, call a paid API, or create synthetic evidence.

## Regression and Acceptance

AppTests first require each related guidance group to share one atomic element. The current split
elements fail that contract. After implementation, focused and full tests, Ruff, the deterministic
12-case benchmark, packaging checks, and `git diff --check` must pass.

A fresh branch workbench session must then repeat the deliberately constructed demo flow and show,
in browser DOM and screenshot evidence, the selected runtime target, E3/E4 meanings, criterion
resolution heading/context, disabled empty runtime save action, and unchanged final-review
acceptance boundary. No runtime record, resolution, or final acceptance will be submitted during
the browser check.

## Out of Scope

- Changing evidence levels, runtime-evidence validation, resolution semantics, or the gate.
- Adding generic review, security scanning, auto-fix, telemetry, paid services, or APIs.
- Treating the deliberately constructed demo or browser screenshot as external adoption proof.
- Publishing a release for this presentation-only unreleased workbench correction.
