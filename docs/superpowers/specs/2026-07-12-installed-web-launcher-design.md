# Installed Web Launcher Design

## Problem

The release wheel contains the complete Streamlit application, but installed users have no supported command to launch it. The only documented web path assumes a source checkout and knowledge of `apps/web/app.py`, so the downloadable wheel exposes only the CLI in practice.

## Decision

Add a separate `scopeproof-web` console script owned by the `apps.web` UI package. Its launcher resolves the packaged `app.py` with `importlib.resources`, invokes `python -m streamlit run` with a fixed argument list, and returns Streamlit's exit code.

The separate entry point preserves the UI-independent core boundary: `scopeproof_core` does not import Streamlit or the launcher. The launcher uses no shell and accepts no repository-controlled command path or arbitrary command arguments. Standard Streamlit environment variables remain available for local headless and port configuration.

## Alternatives

- Add `scopeproof web` inside the core CLI. This couples the core command surface to the Streamlit UI layer.
- Document a shell expression that discovers packaged `app.py`. This is difficult for first-time users and inconsistent across shells.
- Keep source checkout as the only UI path. This leaves the verified wheel incomplete as an adoption path.

## Release

This is a user-visible installed capability, so version 0.1.12 is justified. The protected implementation PR will bump the package version and update the README. After merged-main CI and CodeQL pass, build the wheel from the exact merge commit, create v0.1.12, attach that wheel, redownload it, and verify its digest and runtime. Do not publish any intermediate or additional release.

## Boundaries

- Start only the packaged ScopeProof Streamlit application.
- Never execute reviewed pull-request code.
- Bind and browser behavior remain Streamlit defaults; documentation describes it as a local workbench.
- Add no service, account, organization, billing, paid API, LLM API, license, or new GitHub Action.
- Runtime health proves only that the packaged application starts, not that a reviewed PR is correct.

## Acceptance Criteria

1. `scopeproof-web` is installed from the wheel and resolves the packaged `apps/web/app.py`.
2. The launcher invokes the current interpreter without a shell and returns the child exit code.
3. `scopeproof_core` does not import Streamlit or `apps.web`.
4. README user Quickstart installs v0.1.12, runs the offline benchmark, and starts the local workbench with `scopeproof-web`.
5. A clean-installed wheel returns `ok` from the Streamlit health endpoint.
6. The deterministic demo workflow remains covered by existing AppTest assertions and the full suite.
7. v0.1.12 targets the exact protected-main merge commit and exposes the verified wheel asset.

