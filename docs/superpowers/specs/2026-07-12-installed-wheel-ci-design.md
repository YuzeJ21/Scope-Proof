# Installed Wheel CI Design

## Problem

ScopeProof's required `verify` check validates the editable source checkout but does not build or execute the distributable wheel. A packaging regression can therefore pass protected-main CI even when the installed CLI is incomplete.

## Decision

Add one final `Installed wheel smoke` step to the existing `verify` job. The step will build the project wheel into `$RUNNER_TEMP`, force-install it without resolving dependencies, change the working directory to `$RUNNER_TEMP`, and run `scopeproof benchmark`.

Keeping the smoke check in the existing job reuses the tested Python environment and dependencies. Running it last ensures replacing the editable install cannot affect lint, unit tests, or the source benchmark. Changing out of the checkout prevents Python from accidentally importing repository files instead of installed wheel contents.

## Scope

- Extend the repository workflow contract test before changing CI.
- Build and execute the wheel in the existing required `verify` job.
- Add no Actions, services, accounts, paid APIs, secrets, or dependencies.
- Do not change the benchmark verdict rules or product runtime.
- Do not create a release for this CI-only change.

## Acceptance Criteria

1. The contract test fails when the installed-wheel smoke step is absent.
2. CI builds a wheel with `python -m pip wheel . --no-deps`.
3. CI installs that wheel with `python -m pip install --force-reinstall --no-deps`.
4. CI runs `scopeproof benchmark` from outside the repository checkout.
5. Ruff, the full test suite, the source benchmark, and a local installed-wheel reproduction pass.

## Failure Behavior

Any build, install, or installed benchmark failure makes the required `verify` job fail. No failure is converted into a warning or inferred as product readiness.
