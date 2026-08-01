# Workbench UX simplification verification

## Scope and evidence boundary

- Date: 2026-08-01 (America/Toronto)
- Tested source commit: `1a07eb92e322326ced373288cc5afb96b8cd974d`
- Environment: macOS 26.5.1 (build 25F80), Apple silicon (`arm64`), Codex In-app Browser. The Browser surface did not expose a browser version or user-agent value.
- Local server: `uv run scopeproof-web --host 127.0.0.1 --port 8512`, using isolated temporary home `/tmp/scopeproof-task8-home.GPG9Mw`.
- Health: `GET http://127.0.0.1:8512/_stcore/health` returned `ok`.

This is current-run, owner-operated engineering evidence for a deliberately constructed demo. It does not prove customer usability, production or runtime correctness, cross-platform behavior, assistive-technology compatibility, WCAG conformance, or acceptance-criteria satisfaction. It earns **zero Stage 1 credit**.

## Automated gates

| Command | Result |
| --- | --- |
| `uv run pytest -q tests/apps/test_streamlit_app.py tests/apps/test_view_models.py tests/apps/test_web_app.py tests/test_presentation.py` | Passed: 173 tests in 98.40 seconds. |
| `uv run ruff check apps/web tests/apps` | Passed: `All checks passed!` |

These commands provide focused engineering checks. In particular, source/test definitions remain distinct from executed runtime verification of the constructed repository evidence.

## Desktop walkthrough — actual 1280×720 viewport

### 1. Start Review

![Start Review at 1280 by 720](01-start-review.png)

- Browser measurement reported `window.innerWidth = 1280` and `window.innerHeight = 720`.
- The PR URL input and `Fetch public PR` were first in document order. Their measured tops were 577 px and 631 px.
- The four optional controls followed at measured tops 687, 743, 838, and 894 px: `Try ScopeProof`, `Alpha feedback session (optional)`, `Advanced source options`, and `Resume a saved review`.
- All four optional controls were collapsed.

### 2. Confirm Criteria

![Four confirmed collapsed criteria at 1280 by 720](02-confirm-criteria.png)

- The constructed demo prepared four criteria.
- The early `Confirm criteria` action changed the summary to `Criteria: 4 · Confirmation: Confirmed · Pending edits: None`.
- AC-01 through AC-04 remained collapsed (`details.open = false` for each criterion editor).

### 3. Evidence and ordinary decision

![AC-01 evidence and ordinary decision at 1280 by 720](03-evidence-and-decision.png)

- Analysis produced one compact observed-CI summary: `Observed CI: Passing`, `Collection: Complete`, one successful completed check, and `Runtime verification: Not recorded`.
- AC-01 was selected. Both evidence groups were opened and inspected:
  - Implementation: `EV-AC-01-01` and `EV-AC-01-04`.
  - Test: `EV-AC-01-02` and `EV-AC-01-03`; the UI explicitly described these as test intent, not executed verification.
- The ordinary criterion decision was recorded as `Accepted` by `Local reviewer`. The local review history showed that outcome for AC-01.
- `Record optional external verification (E3/E4)` and `Recorded runtime evidence (0)` remained optional and collapsed.

### 4. Summary, exports, and automatic persistence

![Action-required summary and exports at 1280 by 720](04-summary-and-export.png)

- Summary remained fail-closed at `Review status: Action required` with `Blocking Criteria · Conditional Criteria` after AC-01 was accepted.
- `Download Markdown`, `Download JSON`, and `Download CSV` appeared consecutively before `Local review storage` in document order.
- No manual review-save action was used. The UI reported `Review saved automatically. ID: 695a4625-1837-4f4c-aa1a-841be2a4c5cf.`
- Expanding local storage reported `Saved locally — current review matches local storage`; `Save now` was disabled. The isolated-home JSON file existed and retained `Local reviewer`, the AC-01 acceptance event, and `head-demo-002`.

## Narrow walkthrough — actual 390×844 viewport

![Narrow criterion workspace at 390 by 844](05-narrow-workspace.png)

- Browser measurement reported `window.innerWidth = 390` and `window.innerHeight = 844`.
- Page-level horizontal overflow was not observed: HTML and body each measured `clientWidth = 390` and `scrollWidth = 390`.
- In document order, `Evidence` preceded `Criterion resolution` (heading indices 9 and 12). At the evidence anchor their measured tops were 391 px and 2055 px, respectively, showing the columns had stacked evidence-first.
- Both evidence groups were opened at this width. The open groups exposed all four AC-01 evidence IDs: `EV-AC-01-01`, `EV-AC-01-04`, `EV-AC-01-02`, and `EV-AC-01-03`. The page-level width remained 390 px while they were open.
- At the summary anchor all three download buttons resolved uniquely and were visible, so the downloads remained reachable.
- This is a single macOS/browser narrow-width observation, not mobile-device, cross-platform, or accessibility-conformance evidence.

## Console, keyboard, zoom, and unavailable environments

The walkthrough tab and the separate keyboard-attempt tab each returned an empty warning/error log (`[]`) when queried after the exercised flow. Zero ScopeProof-caused console errors or warnings were observed in this run.

| Check | Result | Current-run observation |
| --- | --- | --- |
| PR URL focus and input | Confirmed | Keyboard-targeted input accepted `https://github.com/octocat/Hello-World/pull/1`; Enter applied the value and enabled Fetch. The input remained the active element during entry. |
| Fetch public PR | Not confirmed | The enabled, unique button received Enter, Space, and focused Enter attempts, but the Browser surface exposed no loading, success, or error state transition. |
| Demo expansion and load | Not confirmed | The unique `Try ScopeProof` summary could be focused by the keyboard harness, but Enter did not change `details.open` from `false`; the demo-load button therefore was not activated in a keyboard-only chain. |
| Criteria confirmation | Not confirmed | A keyboard-only demo-load state could not be established, so the enabled confirmation action was unavailable without mixing pointer setup into this check. |
| Deterministic analysis | Not confirmed | The keyboard-only chain did not reach an enabled analysis action. |
| Criterion selection | Confirmed | ArrowDown opened the four-option criterion list and ArrowDown plus Enter changed the selected criterion from AC-01 to AC-02. |
| Ordinary resolution | Not confirmed | ArrowDown plus Enter selected ordinary `Accepted`, but Enter on `Save resolution` produced no append status. Selection was exercised; persisted submission was not proven. |
| Optional external verification | Not confirmed | Enter on the focused, unique E3/E4 summary left `details.open = false`. |
| Downloads | Not confirmed | Enter was attempted on each unique enabled Markdown, JSON, and CSV download button; no download event was exposed within three seconds for any button. Reachability remains separately confirmed by the pointer/narrow checks above. |
| Actual 200% browser zoom | Not confirmed | Browser documentation and advertised capabilities exposed only `visibility` and `viewport`, with no supported zoom control or measurable 200% zoom result. Viewport resizing was not treated as zoom. |
| Screen reader | Not confirmed | No screen-reader surface was available or exercised. |
| Windows | Not confirmed | Not available in this macOS run. |
| Linux | Not confirmed | Not available in this macOS run. |

Keyboard rows report only the exact exercised interaction. They do not establish full tab order, screen-reader behavior, WCAG conformance, or general keyboard accessibility.

## Conclusion

The constructed demo completed the requested pointer flow at 1280×720 and the bounded responsive checks at 390×844. The observed flow preserved explicit confirmation, deterministic evidence boundaries, a fail-closed action-required summary, exports before local storage, and automatic durable local persistence. Keyboard and zoom limitations remain explicitly `Not confirmed`. This record is engineering evidence only and provides zero Stage 1 credit.

## Release-quality local verification — 2026-08-01

### Evidence target and boundary

- Verification target SHA: `444ea0ea4bd331d2636be9b59ff4cf752e1f0295`.
- This SHA is the local branch head exercised before this verification record was appended. It is not the SHA of the later evidence commit that contains this section.
- This is local engineering evidence for the branch. It does not make the branch public `main`, publish version 0.2.3, establish customer or production evidence, prove runtime correctness, or advance Stage 1.

### Locked environment and source gates

| Command | Current-run result |
| --- | --- |
| `uv sync --extra dev --extra research --locked` | Passed: resolved 60 packages and checked 55 packages. |
| `uv lock --check` | Passed: resolved 60 packages. The `uv.lock` SHA-256 remained `7d86997ce50b722d07c53ccb113402555bc093021df7179132666a6efff17520`, with no lockfile diff. |
| `uv run ruff check .` | Passed: `All checks passed!` |
| `uv run pytest -q` | Passed: 1,663 tests passed and 1 intentional live test was skipped in 107.58 seconds. |
| `uv run scopeproof benchmark` | Passed: 12 cases and 13 criteria executed; 0 mismatches, 0 status mismatches, 0 must-have False Ready outcomes, 0 false blockers, and 0 unexecuted declared categories. |
| `uv run scopeproof comparison-benchmark` | Passed: 2 cases executed; 0 mismatches. Aggregate classifications were 3 added, 1 modified, 1 relocated, 3 removed, and 1 unchanged. The result retained `does_not_advance_stage_1: true`. |
| Combined `pytest` coverage command for `scopeproof_core` and `apps` | Passed: 1,663 tests passed and 1 intentional live test was skipped in 275.02 seconds. Across 8,364 statements, 403 were missed; exact combined coverage was 95.18%, meeting the 95% threshold. |

### Built-package and installed-runtime checks

- A fresh build in `/tmp/scopeproof-workbench-ux-dist-COUQIV` produced `scopeproof-0.2.3-py3-none-any.whl` and `scopeproof-0.2.3.tar.gz`.
- The shell did not initially expose a bare `python` command. An incomplete first build directory, `/tmp/scopeproof-workbench-ux-dist-1MSryK`, was not used for installation or runtime evidence. The complete build was rerun in the fresh directory above after placing the locked Python 3.12.0 interpreter on `PATH`; the requested `python -m venv` command then succeeded.
- The wheel installed successfully into a new virtual environment outside the checkout.
- The installed `scopeproof benchmark` repeated 12 cases and 13 criteria with 0 mismatches, 0 must-have False Ready outcomes, 0 false blockers, and 0 unexecuted declared categories.
- The installed `scopeproof comparison-benchmark` repeated 2 cases with 0 mismatches and aggregate classifications of 3 added, 1 modified, 1 relocated, 3 removed, and 1 unchanged; `does_not_advance_stage_1` remained true.
- The installed `scopeproof-web` process launched from `/tmp` with isolated home `/tmp/scopeproof-workbench-ux-home-CbGUO9` on `127.0.0.1:8513`. `GET /_stcore/health` returned the exact body `ok`.
- The exact installed server session was interrupted. The health endpoint then became unreachable, no listener remained on port 8513, and no matching installed server process remained.
- The Task 8 browser-evidence server was also cleaned up: the exact server was interrupted, its health endpoint became unreachable afterward, and no matching process remained.

### Distribution inventories and temporary-artifact cleanup

| Artifact | Inventory | Forbidden-path scan | SHA-256 |
| --- | ---: | ---: | --- |
| `scopeproof-0.2.3-py3-none-any.whl` | 99 entries | 0 | `39553b2088f07149b1681423262c917b5204a54a32dde47f32eefdbe67daec61` |
| `scopeproof-0.2.3.tar.gz` | 530 entries | 0 | `2294786fa911b12c61821b658110f3c9f037fe7009ebada15680bb2c52a9f37c` |

The inventory scan covered `.scopeproof`, coverage outputs, virtual environments, `.git` data, local tool/worktree data, bytecode, common credential filenames, local-review artifacts, and generated cache/build directories. Neither archive contained a matching path. The complete build directory, incomplete first-attempt directory, and isolated runtime home were removed after inventory evidence was captured; no distribution, virtual environment, server state, or local-review artifact was left in the checkout.

### Repository hygiene qualification

- `git diff --check origin/main...HEAD` passed with no output. Before commit, `git status --short --branch` showed only this verification document modified on a branch 15 commits ahead of `origin/main`.
- The literal required tracked scan, `git ls-files | rg '(^|/)(\.coverage|\.scopeproof|\.venv|__pycache__)(/|$)|\.pyc$'`, exited 0 and returned `.scopeproof/requirements-confirmation.json` and `.scopeproof/requirements.txt`. The expected-empty assertion therefore did **not** pass.
- This is an inherited baseline false-positive, not new generated branch content: both paths already exist on `origin/main`, there is no branch diff under `.scopeproof`, and their history predates this branch. `docs/github-action.md` requires the two checked-in Action inputs, while `.github/workflows/scopeproof.yml` validates and consumes them.
- Supplemental branch-diff scan `git diff --name-only origin/main...HEAD | rg '(^|/)(\.coverage|\.scopeproof|\.venv|__pycache__)(/|$)|\.pyc$'` exited 1 with no matches, proving this branch introduces no path covered by the forbidden-generated-path pattern.
- The narrow `git ls-files .scopeproof` inventory contained exactly the two intentional requirements inputs above. A targeted scan found no tracked review, alpha-case, rehearsal, research, or local-review JSON data under `.scopeproof`.
