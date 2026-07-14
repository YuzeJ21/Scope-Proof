# Loaded Source Identity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show the validated public-PR identity persistently before an operator confirms acceptance criteria.

**Architecture:** Add one Streamlit-only renderer that consumes the existing validated `PullRequestSnapshot` in session state. Render it after source notices and before criteria entry so it persists across reruns without changing core models, storage, analysis, or gate behavior.

**Tech Stack:** Python 3.12, Streamlit, Pydantic v2 models, pytest `AppTest`, Ruff.

## Global Constraints

- ScopeProof is an evidence assistant, not a correctness oracle.
- Users must confirm normalized acceptance criteria before analysis.
- Keep the core engine independent from Streamlit and GitHub UI layers.
- Do not execute untrusted repository code.
- Treat False Ready as more harmful than False Blocked.

---

### Task 1: Persistently render the validated loaded-source identity

**Files:**
- Modify: `apps/web/app.py`
- Test: `tests/apps/test_streamlit_app.py`

**Interfaces:**
- Consumes: `PullRequestSnapshot.repository`, `pr_number`, `head_sha`, `files`, and `ingestion_state`.
- Produces: `_render_loaded_source_identity(snapshot: PullRequestSnapshot) -> None` and a persistent pre-confirmation UI summary.

- [ ] **Step 1: Write the failing Streamlit regression test**

Add a test that uses `load_demo_snapshot().model_copy(...)` to provide a validated public identity,
patches `GitHubClient.fetch_pull_request`, clicks `fetch_pr`, and asserts the rendered Markdown/code/
caption text contains `acme/widget · PR #7`, the complete 40-character head SHA,
`2 changed files fetched`, and `Complete ingestion`. Also assert `run_analysis` remains disabled.

- [ ] **Step 2: Run the focused test and verify the provenance summary is missing**

Run:

```bash
PYTHONPATH="$PWD" '/Users/yjian070/Documents/New project 2/.venv/bin/python' \
  -m pytest tests/apps/test_streamlit_app.py::test_loaded_public_pr_shows_validated_source_identity_before_criteria_confirmation -q
```

Expected: FAIL because the current UI renders only the one-time generic success notice.

- [ ] **Step 3: Implement the minimal persistent renderer**

Add `_render_loaded_source_identity(snapshot: PullRequestSnapshot) -> None` near the existing ingestion
renderer. Use a bordered `st.container`, a bold `Loaded source` label, a repository/PR line, a code
block containing the full head SHA, and a caption with singular/plural changed-file copy and the
status-formatted ingestion state. Invoke it whenever the current session snapshot is not `None`,
after source notices and before ingestion limitations.

- [ ] **Step 4: Run focused Streamlit coverage**

Run:

```bash
PYTHONPATH="$PWD" '/Users/yjian070/Documents/New project 2/.venv/bin/python' \
  -m pytest tests/apps/test_streamlit_app.py -k 'loaded_public_pr or partial_public_pr or source_reload' -q
```

Expected: the new regression and existing partial/reload tests pass.

- [ ] **Step 5: Run complete verification**

Run:

```bash
PYTHONPATH="$PWD" '/Users/yjian070/Documents/New project 2/.venv/bin/python' -m ruff check .
PYTHONPATH="$PWD" '/Users/yjian070/Documents/New project 2/.venv/bin/python' -m pytest -q
PYTHONPATH="$PWD" '/Users/yjian070/Documents/New project 2/.venv/bin/python' -m scopeproof_core.cli benchmark
git diff --check
```

Expected: Ruff passes; all offline tests pass except the one intentional live-network skip; the
benchmark executes 12 cases and 13 criteria with zero mismatches, zero must-have False Ready, zero
False Blocker, and zero unexecuted categories; diff hygiene is clean.

- [ ] **Step 6: Verify the real local flow visually**

Start the branch application locally, fetch `https://github.com/octocat/Hello-World/pull/1` without
a token, and capture the loaded state before entering criteria. Require the visible summary to show
`octocat/Hello-World`, `PR #1`, the complete fetched head SHA, changed-file count, and `Complete
ingestion`; analysis must remain locked.

- [ ] **Step 7: Commit the bounded slice**

```bash
git add apps/web/app.py tests/apps/test_streamlit_app.py \
  docs/superpowers/specs/2026-07-14-loaded-source-identity-design.md \
  docs/superpowers/plans/2026-07-14-loaded-source-identity.md
git commit -m "feat: show loaded source identity"
```
