# Review Version Provenance Design

## Problem

ScopeProof 0.1.14 creates new reviews whose `tool_version` is still `0.1.0`. The field was
introduced as a literal default in the `Review` schema and was never connected to the package
version. Later releases updated only `pyproject.toml`, so CLI, Streamlit, persisted records, and
exports now report inaccurate producer provenance.

This is not only a development-environment mismatch. A real CLI review created from the current
main branch persisted and exported `tool_version: 0.1.0`. The local editable distribution metadata
also reports an older installed version, so runtime lookup through `importlib.metadata` cannot be
the source of truth for source-checkout execution.

## Decision

Create `scopeproof_core/version.py` with one explicit `__version__` constant. Configure Hatch's
built-in version source to read that file by making the project version dynamic. Import the same
constant when constructing new `Review` models.

This makes the packaged distribution version and new review provenance derive from one checked-in
source without adding a dependency or reading repository files at runtime.

Because `main` already contains unreleased changes after the published v0.1.14 tag, the checked-in
source version becomes `0.1.15.dev0`. This prevents source-checkout reviews from impersonating the
published v0.1.14 wheel. README installation guidance and the existing release remain v0.1.14.

## Data and Compatibility Contract

- New `Review` objects default `tool_version` from `scopeproof_core.version.__version__`.
- The current unreleased main line reports `0.1.15.dev0`; a future release changes the same single
  source to its final release version.
- CLI, Streamlit, demo, persistence, and every export continue using the validated `Review` model,
  so no UI-specific or command-specific version override is added.
- Explicitly supplied `tool_version` values remain valid. Loading an older saved review preserves
  the version originally stored; ScopeProof does not rewrite historical provenance.
- The record schema version and ruleset version are unchanged.
- Evidence, gate, runtime-evidence, resolution, and final-acceptance semantics are unchanged.

## Packaging Contract

`pyproject.toml` declares `dynamic = ["version"]` and points `[tool.hatch.version]` at
`scopeproof_core/version.py`. Building a wheel from a clean checkout must produce a filename and
installed distribution version that match `__version__`.

`scopeproof_core.__version__` is exported for conventional programmatic inspection. The core
package remains independent from Streamlit and does not import packaging metadata.

## Alternatives Rejected

1. Keep a literal in both `pyproject.toml` and Python, then add a drift test. This detects mistakes
   but retains two values that every release must edit.
2. Use `importlib.metadata.version("scopeproof")`. It works for an installed wheel but can be
   missing or stale during source and editable execution; the current environment already reports
   0.1.6 while the checkout is 0.1.14.
3. Parse `pyproject.toml` at runtime. Released wheels do not need to contain that repository file,
   and a core model should not depend on the current working directory.

## Failure and Safety Behavior

- A packaging configuration that cannot extract the version fails the wheel build rather than
  silently publishing an unknown version.
- Repository contract tests fail if the dynamic version source is removed or redirected.
- Installed-wheel smoke tests validate distribution metadata and a newly constructed review.
- No review data is upgraded automatically, and no external service, API, billing, repository-code
  execution, or synthetic validation is introduced.

## Verification

Regression coverage must prove:

- a new `Review` uses the single source version;
- an explicit historical `tool_version` survives validation and JSON round-trip;
- Hatch is configured to read the single source;
- a freshly built and clean-installed wheel reports the same distribution, module, and review
  version;
- a real CLI fixture review persists and exports that version;
- all existing tests, deterministic benchmark cases, and repository hygiene gates remain green.

No release is published for this bounded correction alone. The next release can include it as part
of a coherent user-facing batch.
