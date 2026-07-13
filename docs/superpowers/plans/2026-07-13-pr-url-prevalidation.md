# Public PR URL Prevalidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent malformed public GitHub pull-request URLs from appearing fetchable and provide precise recovery guidance before any request.

**Architecture:** Reuse `scopeproof_core.github.client.parse_pr_url` inside the Streamlit entry flow to derive one `pr_url_is_valid` boolean. The UI uses that boolean for warning and button state, while `GitHubClient.fetch_pull_request` keeps its existing parser call as defense in depth.

**Tech Stack:** Python 3.12, Streamlit AppTest, pytest, Pydantic-backed ScopeProof core, Ruff.

## Global Constraints

- Keep ScopeProof deterministic, local-first, public-repository-only, informational, and non-blocking.
- Never execute untrusted pull-request code.
- Do not create validation evidence from URL-shape validation.
- Do not change criteria confirmation, evidence retrieval, findings, gate, export, or persistence semantics.
- Reuse `parse_pr_url`; do not add a second URL regex.
- Use this exact malformed-value copy: `Enter a public GitHub pull request URL in this format: \`https://github.com/OWNER/REPO/pull/NUMBER\`.`
- Keep blank input neutral and disabled.

---

### Task 1: Add the first-use URL-shape contract

**Files:**
- Modify: `tests/apps/test_streamlit_app.py:45-65`
- Modify: `apps/web/app.py:21`
- Modify: `apps/web/app.py:227-264`

**Interfaces:**
- Consumes: `parse_pr_url(url: str) -> tuple[str, str, int]` and `InvalidPullRequestUrl` from `scopeproof_core.github.client`.
- Produces: a rerun-local `pr_url_is_valid: bool`; no new public API or persisted field.

- [ ] **Step 1: Write the failing AppTest regression**

Add these tests after `test_product_disclaimer_is_visible`:

```python
def test_malformed_public_pr_url_shows_format_guidance_and_disables_fetch() -> None:
    app = new_app()
    app = app.text_input(key="pr_url").set_value(
        "https://github.com/acme/widget/pull/not-a-number"
    ).run()

    warning_text = "\n".join(item.value for item in app.warning)
    assert (
        "Enter a public GitHub pull request URL in this format: "
        "`https://github.com/OWNER/REPO/pull/NUMBER`."
    ) in warning_text
    assert app.button(key="fetch_pr").disabled is True


def test_canonical_public_pr_url_enables_fetch_without_format_warning() -> None:
    app = new_app()
    app = app.text_input(key="pr_url").set_value(
        "https://github.com/acme/widget/pull/42"
    ).run()

    warning_text = "\n".join(item.value for item in app.warning)
    assert "Enter a public GitHub pull request URL" not in warning_text
    assert app.button(key="fetch_pr").disabled is False
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```bash
'/Users/yjian070/Documents/New project 2/.venv/bin/python' -m pytest \
  tests/apps/test_streamlit_app.py -q \
  -k 'malformed_public_pr_url or canonical_public_pr_url'
```

Expected: the malformed test fails because no format warning exists and the
fetch button is enabled. The canonical test may already pass; the RED evidence
must come from the missing malformed-state behavior.

- [ ] **Step 3: Import the existing parser and error type**

Replace the single-line GitHub import in `apps/web/app.py` with:

```python
from scopeproof_core.github.client import (
    GitHubClient,
    GitHubIngestionError,
    InvalidPullRequestUrl,
    parse_pr_url,
)
```

- [ ] **Step 4: Derive the validation state and render recovery guidance**

Immediately after the `pr_url` text input, add:

```python
pr_url_is_valid = False
if pr_url.strip():
    try:
        parse_pr_url(pr_url)
    except InvalidPullRequestUrl:
        st.warning(
            "Enter a public GitHub pull request URL in this format: "
            "`https://github.com/OWNER/REPO/pull/NUMBER`."
        )
    else:
        pr_url_is_valid = True
```

Change the fetch button condition to:

```python
disabled=not pr_url_is_valid or replacement_blocked,
```

- [ ] **Step 5: Run focused tests and verify GREEN**

Run the Step 2 command.

Expected: `2 passed` and no Streamlit exception or warning.

- [ ] **Step 6: Run focused regression coverage**

Run:

```bash
'/Users/yjian070/Documents/New project 2/.venv/bin/python' -m pytest \
  tests/apps/test_streamlit_app.py tests/github/test_client.py -q
'/Users/yjian070/Documents/New project 2/.venv/bin/python' -m ruff check \
  apps/web/app.py tests/apps/test_streamlit_app.py
```

Expected: all selected tests and Ruff pass.

- [ ] **Step 7: Commit the implementation**

```bash
git add apps/web/app.py tests/apps/test_streamlit_app.py
git commit -m "fix: validate public PR URL before fetch"
```

### Task 2: Verify distribution and live behavior

**Files:**
- Verify only; no planned source edits.

**Interfaces:**
- Consumes: the completed Task 1 branch.
- Produces: local verification evidence and protected-PR evidence; no repository artifact.

- [ ] **Step 1: Run complete static and deterministic verification**

```bash
'/Users/yjian070/Documents/New project 2/.venv/bin/python' -m ruff check .
'/Users/yjian070/Documents/New project 2/.venv/bin/python' -m pytest -q
'/Users/yjian070/Documents/New project 2/.venv/bin/python' -m scopeproof_core.evals.runner
git diff origin/main...HEAD --check
```

Expected: Ruff passes; the complete suite passes with only the documented skip;
all 12 benchmark cases execute with zero mismatches, zero must-have False Ready,
and zero False Blocker; diff check is clean.

- [ ] **Step 2: Verify the built wheel and packaged server**

Build a `0.1.15.dev0` wheel into a fresh `/tmp` directory, install it into a
fresh virtual environment with dependencies, verify installed metadata and
`scopeproof-web --version`, run `scopeproof benchmark`, launch the packaged
workbench on an unused loopback port, and require `/_stcore/health` to return
exactly `ok`.

- [ ] **Step 3: Verify the first-use states in the in-app browser**

Start the branch workbench with temporary `HOME`, then capture and inspect:

1. blank URL: no format warning, fetch disabled;
2. malformed URL: exact warning visible, fetch disabled, no request error;
3. canonical URL: warning absent and fetch enabled;
4. deliberately constructed demo still loads and reaches criteria confirmation.

- [ ] **Step 4: Publish through protected main**

Push `codex/pr-url-prevalidation`, open a pull request without reviewers or
comments, wait for required `verify` and CodeQL checks, merge only when green,
verify merged-main CI and CodeQL, fast-forward local `main`, and remove the
worktree and local/remote feature branches.
