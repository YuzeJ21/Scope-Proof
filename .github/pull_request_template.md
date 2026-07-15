## User-confirmed requirement

Describe the requirement or reproducible defect this change addresses. Link its source and state who
confirmed it. Do not invent acceptance criteria to justify an implementation.

## Evidence and change

- Evidence level before the change:
- Files or behavior changed:
- Why this is the smallest safe slice:

Static evidence is not runtime verification. Separate implementation, automated-test, external
runtime, and human-acceptance evidence.

## Verification

- [ ] Focused regression failed before the fix and passes after it, when behavior changed.
- [ ] `python -m ruff check .`
- [ ] `python -m pytest -q`
- [ ] `python -m scopeproof_core.evals.runner`
- [ ] No untrusted repository code was executed.
- [ ] Persisted or exported object changes remain Pydantic-validated.

## Remaining limitations

State what is not verified, any partial-ingestion boundary, and the human decision still required.
