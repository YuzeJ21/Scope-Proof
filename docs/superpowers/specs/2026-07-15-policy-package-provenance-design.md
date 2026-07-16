# ScopeProof Packaged Use-Policy Provenance Design

## Context

ScopeProof now records its evaluation-only posture in the repository-root `USE_POLICY.md`, but a
wheel built from protected `main` contains neither that document nor a package-metadata link to it.
This was reproduced by building `scopeproof-0.1.22.dev0-py3-none-any.whl` and inspecting its ZIP
members and `.dist-info/METADATA`.

The gap is package provenance, not product behavior. It does not justify publishing v0.1.22 and
does not create runtime or adoption evidence.

## Decision

Keep `USE_POLICY.md` as the single policy source. Configure Hatch's existing wheel
`force-include` mapping so the exact source bytes are installed as
`scopeproof_core/USE_POLICY.md`. Add a normal project URL named `Use Policy` pointing to the
repository's canonical policy document.

Do not set a PEP 639 `license-files` entry, SPDX expression, recognized open-source license,
classifier, or `License` metadata field. The packaged path and project URL improve discovery
without presenting the evaluation-only policy as an open-source license.

## Considered approaches

1. **Package data plus a project URL — selected.** Works offline after installation, remains
   discoverable in package metadata, and avoids standardized license metadata.
2. **Project URL only — rejected.** Discoverable but unavailable offline and unable to prove which
   policy bytes accompanied the wheel.
3. **PEP 639 `License-File` — rejected.** Technically conventional for legal text, but it would
   create an avoidable license-metadata signal after the owner explicitly chose a no-open-source-
   license posture.

## Repository changes

- `pyproject.toml` adds `[project.urls]` with the exact `Use Policy` URL.
- The existing wheel `force-include` table maps root `USE_POLICY.md` to
  `scopeproof_core/USE_POLICY.md` alongside the existing benchmark corpus mapping.
- `tests/test_repository_contracts.py` protects the exact metadata and wheel mapping while also
  rejecting `license`, `license-files`, and license classifiers.
- `CHANGELOG.md` records the unreleased package-provenance improvement without claiming that the
  published v0.1.21 wheel contains it.

No application code, schema, gate, exporter, Streamlit flow, GitHub Action behavior, dependency,
or version changes.

## Verification

Use test-driven development: first add a repository contract that fails against the current
configuration, then implement the minimal metadata and force-include entries. Run repository
contracts, Ruff, the full Python 3.12 coverage gate, the deterministic benchmark, dependency
integrity, YAML validation, and `git diff --check`.

Build a fresh wheel outside the checkout and require:

- exactly one `scopeproof_core/USE_POLICY.md` member;
- its bytes equal the root `USE_POLICY.md` bytes;
- `.dist-info/METADATA` contains the `Use Policy` project URL;
- `.dist-info/METADATA` contains no `License`, `License-Expression`, or `License-File` header;
- the wheel installs cleanly and both CLI version commands plus the benchmark succeed.

## Publication boundary

Publish through one ready protected-main pull request. Merge only after Python 3.11, `verify`, and
CodeQL succeed. Confirm merged-main CI and CodeQL, then clean the owned worktree and branch. Do not
publish v0.1.22, comment on issue #3, create a monitor, or manufacture first-use evidence.
