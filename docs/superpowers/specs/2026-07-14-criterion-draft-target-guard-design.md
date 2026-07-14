# Criterion Draft Target Guard Design

## Reproduced gap

Current-main Streamlit AppTest evidence filled a complete manual runtime record while
`AC-01` was selected, then changed `Inspect criterion` to `AC-03`. All five values
remained populated, Save remained enabled, and the unchanged `AC-01` scenario was
persisted with `criterion_id="AC-03"`.

The same criterion selector targets the human-resolution controls. Their unsaved
decision and note also survive a target change. The persisted Pydantic objects and
lifecycle services validate structure and criterion membership, but they cannot know
that a human entered the draft for a different active criterion.

## Decision

Bind unsaved criterion-detail inputs to a session-only target made from the active
review ID, reviewed head SHA, criteria revision number, and selected criterion ID.
When that target changes:

- clear all unsaved manual-runtime-evidence inputs and restore E3;
- clear the unsaved resolution decision, note, and claimed evidence level;
- leave all previously appended runtime evidence and resolution events unchanged;
- show one concise notice only when an unsaved input actually existed, naming the new
  criterion and asking the reviewer to re-enter the observation or decision for it.

The target guard runs after `Inspect criterion` is resolved and before either form's
widgets are instantiated, so Streamlit session state can be reset deterministically.

## Alternatives considered

1. **Reset drafts on target change** — selected because it prevents wrong-criterion
   evidence and decisions with small, visible presentation-state behavior.
2. **Keep the draft and silently retarget it** — rejected because this is the current
   evidence-integrity defect.
3. **Pin the form to its original criterion** — rejected because the form lives inside
   the currently selected criterion detail and would contradict the visible context.
4. **Store a separate draft per criterion** — rejected for this bounded slice because
   it adds a larger transient-draft state model and leaves cross-review/revision
   invalidation to solve separately.

## Architecture and data flow

Only `apps/web/app.py` presentation state changes. A small helper detects whether any
runtime or resolution draft input exists, clears the known widget keys, and returns
whether a notice is warranted. The selected target token is session-only and is never
persisted or exported.

`RuntimeEvidence`, `ResolutionEvent`, `append_runtime_evidence`,
`append_resolution`, deterministic gate evaluation, final acceptance, storage, and
exporters remain authoritative and unchanged.

## Verification

- Add an AppTest that fills a complete AC-01 runtime draft, changes to AC-03, and
  requires cleared fields, disabled Save, a recovery notice, and no appended record.
- In the same target-change contract, populate a resolution draft and require it to
  clear without appending an event.
- Prove changing criterion with no pending inputs does not display a discard notice.
- Preserve existing tests for valid runtime append, resolution append, successful-form
  resets, target context, final acceptance, and deterministic gates.
- Run focused tests, Ruff, the complete offline suite, deterministic benchmark,
  `git diff --check`, and loopback Streamlit health.

## Evidence limits and boundaries

The reproduction and AppTests prove local workbench target-state behavior only. They
are not external PR evidence, runtime verification for a reviewed PR, user adoption,
or proof of correctness. No untrusted repository code, paid API/LLM, billing, fork,
organization, private repository, synthetic validation, GitHub notification, schema,
gate, release, or persisted evidence semantics change.
