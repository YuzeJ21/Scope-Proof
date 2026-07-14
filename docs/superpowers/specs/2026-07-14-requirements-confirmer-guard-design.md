# Requirements Confirmer Guard Design

## Problem

The checked-in GitHub Action confirmation record binds requirements bytes to an owner-supplied
identity and timestamp. `RequirementsConfirmation.confirmed_by` currently has only
`min_length=1`, so whitespace-only identities such as `"   "` pass Pydantic validation.

The workflow treats a successful validation command as authoritative: it sets
`SCOPEPROOF_REQUIREMENTS_CONFIRMED=true`, analyzes the pull request, and permits the informational
same-repository comment path. A whitespace-only identity therefore crosses the user-confirmation
boundary even though no confirmer or role is actually recorded.

## Root cause

The digest and timestamp contracts are valid. The defect is localized to string semantics at the
Pydantic boundary: character length does not establish non-whitespace identity. Equivalent
human-supplied Action and runtime records already use field validators for this reason.

## Approaches considered

1. **Pydantic field validator — selected.** Reject whitespace-only `confirmed_by` values in
   `RequirementsConfirmation`. This protects direct model use, the CLI, and the workflow with one
   deterministic rule.
2. **CLI post-load check.** This protects only `scopeproof validate-requirements-confirmation` and
   leaves direct callers able to create invalid confirmation objects.
3. **Workflow shell check.** This duplicates a domain rule in YAML and leaves local validation and
   future adapters unprotected.

## Design

Add a `field_validator("confirmed_by")` that raises
`ValueError("confirmed_by must contain non-whitespace text")` when `value.strip()` is empty. Return
the original value unchanged so a valid owner name or role is not silently normalized.

Regression tests cover empty, spaces-only, and tab/newline-only values through the file-backed
validation function. A preservation test proves surrounding whitespace remains byte-for-byte
unchanged. A CLI test proves invalid records fail through the existing parser recovery path rather
than setting a confirmed state.

## Scope boundaries

The change does not alter the requirements digest, timestamp format, requirements text, workflow
permissions, comment rules, gate semantics, public-repository boundary, or version. It does not
claim the supplied identity is externally authenticated; it proves only that the owner-supplied
confirmation record contains explicit non-whitespace identity context.

## Verification

Run focused confirmation and CLI tests, Ruff, the complete offline suite, deterministic benchmark,
`git diff --check`, an archived-wheel install, an installed source-independent confirmation probe,
and loopback workbench health. Integrate only through a green protected PR and verify CI and CodeQL
on the exact merge SHA.

These checks are controlled schema, CLI, packaging, benchmark, and loopback-health evidence. They
are not external PR runtime evidence, authenticated identity, customer validation, or adoption.
No billing, paid API or LLM, private repository, organization, second account, fork test, synthetic
validation, or invented evidence is involved.
