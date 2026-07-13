# Installed Web CI Smoke Design

## Problem

The required `verify` job builds and installs the ScopeProof wheel, then runs only `scopeproof benchmark`. The v0.1.12 wheel adds the user-facing `scopeproof-web` entry point, but CI does not prove that the entry point, packaged app resource, Streamlit import, and local server startup work together.

## Decision

Extend the existing final `Installed wheel smoke` step. After the installed benchmark passes, start `scopeproof-web` in a new Linux process group with Streamlit configured through environment variables for headless loopback operation on port 8512. Poll `http://127.0.0.1:8512/_stcore/health` for at most 30 seconds and require the exact body `ok`.

Register a shell `trap` before polling. On every success or failure path, terminate the whole process group and wait for the launcher so neither the launcher nor its Streamlit child survives the step. If the launcher exits early or health never becomes ready, print the bounded local log and fail `verify`.

## Alternatives

- A separate job gives more isolation but repeats checkout, Python setup, dependency installation, tests, and wheel building.
- Checking only `command -v scopeproof-web` cannot detect a missing packaged app or runtime startup failure.
- A repository Python helper would be more code than this fixed single-platform CI orchestration requires.

## Boundaries

- Run only the trusted ScopeProof wheel built from the checked-out branch.
- Never fetch or execute pull-request repository code.
- Bind only to `127.0.0.1` and run headlessly.
- Health is package-startup evidence only, not reviewed-PR runtime verification.
- Add no Action, service, account, API, dependency, release, or license.

## Acceptance Criteria

1. The repository contract fails if CI does not run `scopeproof-web` from the installed wheel.
2. CI configures headless mode, loopback address, and a fixed port.
3. CI requires the health body to equal `ok` within 30 attempts.
4. CI checks for early launcher exit and emits the local log on failure.
5. CI always kills and waits for the whole web process group.
6. Existing lint, tests, source benchmark, and installed benchmark remain unchanged and pass.
7. The change merges through protected main without creating a release.

