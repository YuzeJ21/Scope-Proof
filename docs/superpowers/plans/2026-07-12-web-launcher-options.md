# Web Launcher Options Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the installed `scopeproof-web` command deterministically honor friendly host, port, and headless options.

**Architecture:** Keep argument ownership inside `apps.web.launcher`, parse a deliberately small public CLI, and translate it into Streamlit configuration arguments before the packaged application path. Preserve the existing subprocess, interpreter, exit-code, and interrupt behavior.

**Tech Stack:** Python 3.11+, Argparse, importlib.resources, subprocess, pytest, Streamlit, Hatchling.

## Global Constraints

- Default host is `127.0.0.1`, default port is `8501`, and default headless mode is enabled.
- Ports outside `1..65535`, unknown options, and malformed values exit 2 before Streamlit starts.
- Do not forward arbitrary Streamlit options.
- Never execute repository code from a reviewed pull request.
- No new runtime dependency, paid API, billing, fork, or external account.
- Release only from an exact protected-main commit after clean-installed runtime verification.

---

### Task 1: Launcher argument contract

**Files:**
- Modify: `tests/apps/test_web_launcher.py`
- Modify: `apps/web/launcher.py`

**Interfaces:**
- Consumes: console entry point `apps.web.launcher:main` and `sys.argv[1:]`.
- Produces: `main(argv: list[str] | None = None) -> int` and an internal bounded port parser.

- [ ] **Step 1: Write the failing subprocess-vector test**

Extend the existing launcher test to call:

```python
launcher.main(["--host", "127.0.0.2", "--port", "8765", "--no-headless"])
```

Assert the command equals the current interpreter plus `streamlit run`, followed by
`--server.address=127.0.0.2`, `--server.port=8765`, `--server.headless=false`, and the packaged
`app.py` path.

- [ ] **Step 2: Run the focused test and verify RED**

Run: `.venv/bin/python -m pytest tests/apps/test_web_launcher.py -q`

Expected: failure because `main` does not accept an argument list and the old command omits every
requested setting.

- [ ] **Step 3: Implement the minimal owned parser and translation**

Use `argparse.ArgumentParser`, a port type that raises `ArgumentTypeError` outside `1..65535`, and
`BooleanOptionalAction` for headless mode. Build the subprocess vector with the three explicit
Streamlit options before the packaged app path.

- [ ] **Step 4: Add invalid-input regression coverage**

Parameterize ports `0` and `65536`; assert `SystemExit.code == 2`, no subprocess call, concise
`1..65535` stderr, and no traceback. Add an unknown-option case with the same no-launch behavior.

- [ ] **Step 5: Run focused tests and verify GREEN**

Run: `.venv/bin/python -m pytest tests/apps/test_web_launcher.py -q`

Expected: all launcher tests pass.

- [ ] **Step 6: Commit the independently reviewed launcher behavior**

```bash
git add apps/web/launcher.py tests/apps/test_web_launcher.py
git commit -m "fix: honor web launcher options"
```

### Task 2: Installed workflow and release contract

**Files:**
- Modify: `README.md`
- Modify: `.github/workflows/ci.yml`
- Modify: `pyproject.toml`
- Modify: `tests/test_repository_contracts.py`

**Interfaces:**
- Consumes: `scopeproof-web --host HOST --port PORT` from Task 1.
- Produces: v0.1.14 install guidance and CI runtime evidence on explicit port `8512`.

- [ ] **Step 1: Write failing repository contract assertions**

Require version `0.1.14`, v0.1.14 wheel/checksum URLs, README explicit launcher options, and CI
invocation `scopeproof-web --host 127.0.0.1 --port 8512`.

- [ ] **Step 2: Run repository contracts and verify RED**

Run: `.venv/bin/python -m pytest tests/test_repository_contracts.py -q`

Expected: failures on the old version, URLs, README example, and environment-only CI invocation.

- [ ] **Step 3: Update package, README, and CI**

Bump to `0.1.14`, update both release-asset URLs and checksum commands, document explicit launcher
options, and replace CI's address/port environment variables with the public launcher arguments.
Keep `STREAMLIT_SERVER_HEADLESS=true` only if needed; otherwise exercise the default headless
contract directly.

- [ ] **Step 4: Run focused repository and launcher tests**

Run: `.venv/bin/python -m pytest tests/apps/test_web_launcher.py tests/test_repository_contracts.py -q`

Expected: all focused tests pass.

- [ ] **Step 5: Commit the installation contract**

```bash
git add README.md .github/workflows/ci.yml pyproject.toml tests/test_repository_contracts.py
git commit -m "docs: publish deterministic web startup"
```

### Task 3: Verification and protected publication

**Files:**
- Verify only; no planned source edits.

**Interfaces:**
- Consumes: exact branch and later merged-main commit.
- Produces: source, wheel, runtime, GitHub CI, checksum, and release evidence.

- [ ] **Step 1: Run all local gates**

Run Ruff, full pytest, deterministic benchmark, `git diff --check`, and clean-tree inspection.
Expected: no lint errors; all tests pass; 12 benchmark cases with zero mismatches, zero False Ready,
and zero false blocker.

- [ ] **Step 2: Build and clean-install the branch wheel**

Build from an archive, install into a fresh temporary virtual environment, start
`scopeproof-web --host 127.0.0.1 --port 8768`, and require exact `ok` from
`http://127.0.0.1:8768/_stcore/health`. Stop the process group and require no traceback.

- [ ] **Step 3: Publish through protected main**

Push `codex/web-launcher-options`, open a PR, wait for both `verify` runs, evidence review, and
CodeQL, merge normally, then wait for exact merged-main CI, CodeQL, and dependency graph success.

- [ ] **Step 4: Build and publish v0.1.14 from exact merged main**

Build the wheel from `git archive MERGE_SHA`, create its `.sha256`, clean-install and rerun the
benchmark/runtime smoke, publish both assets targeting `MERGE_SHA`, then redownload and repeat
checksum, installation, and non-default-port health verification.

- [ ] **Step 5: Reconcile public state**

Require latest release v0.1.14, exact tag SHA, zero open PRs, only main remote branch, required
`verify`, SHA-pinned Actions, ignored repository notifications, and zero open Dependabot, CodeQL,
or secret-scanning alerts. Do not post an issue announcement.
