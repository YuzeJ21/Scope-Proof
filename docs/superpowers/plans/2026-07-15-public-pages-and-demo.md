# ScopeProof Public Pages and Captioned Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish a free, truthful GitHub Pages landing page and a 60-second captioned constructed
demo without analytics, paid services, or invented validation.

**Architecture:** Build a dependency-free static site under `site/`. Generate one deterministic
MP4/VTT asset from the bundled constructed demo and deploy only `site/` using a SHA-pinned Pages
workflow.

**Tech Stack:** HTML5, CSS, small local JavaScript only if essential, PNG, MP4/H.264, WebVTT,
GitHub Pages Actions.

## Global Constraints

- GitHub Pages public-repository hosting only; no billing integration.
- No analytics, cookies, forms, trackers, remote fonts, customer logos, testimonials, or outcome
  claims.
- The demo is deliberately constructed and is never described as a real incident.
- Likes, views, stars, impressions, and downloads are not product validation.
- Every third-party Action is pinned to an immutable SHA.
- The video is exactly 60 seconds and has equivalent captions and transcript.

---

### Task 1: Define the public-site contract

**Files:**
- Modify: `tests/test_repository_contracts.py`

- [ ] **Step 1: Add failing site and media contracts**

Require `site/index.html`, `site/styles.css`, `site/assets/scopeproof-captioned-demo.mp4`,
`site/assets/scopeproof-captioned-demo.vtt`, and `site/demo-transcript.html`. Require repository,
v0.1.22, quickstart, use-policy, and DM CTA links; exact demo disclosure; the five-stage workflow;
no analytics/remote scripts/forms; semantic video captions; a no-validation-metrics statement;
PNG poster; and an automated media duration between 59.9 and 60.1 seconds.

- [ ] **Step 2: Verify RED**

Run the focused contracts and require missing-file failures.

- [ ] **Step 3: Commit the red contracts**

Commit as `test: define public Pages contract`.

### Task 2: Build the accessible static site

**Files:**
- Create: `site/index.html`
- Create: `site/styles.css`
- Create: `site/demo-transcript.html`
- Create: `site/assets/scopeproof-linkedin-alpha.png`
- Create: `site/assets/scopeproof-demo-poster.jpg`

- [ ] **Step 1: Write semantic page content**

Use header/main/footer, one H1, descriptive links, visible focus, reduced-motion CSS, responsive
cards, and local assets. Include the exact disclosure and no-validation-metrics statement.

- [ ] **Step 2: Copy approved image and create poster**

Copy the approved LinkedIn alpha image into `site/assets`. Create a 16:9 poster from the existing
constructed-demo screenshot with exact disclosure overlaid deterministically.

- [ ] **Step 3: Write the transcript page**

Match the five timed segments in `docs/launch/demo-script.md` and repeat the required disclosure.

- [ ] **Step 4: Run static contracts**

Require HTML/CSS/copy tests to pass while media-duration and workflow tests remain red.

- [ ] **Step 5: Commit**

Commit as `docs: build ScopeProof public landing page`.

### Task 3: Produce and inspect the captioned demo

**Files:**
- Create: `site/assets/scopeproof-captioned-demo.mp4`
- Create: `site/assets/scopeproof-captioned-demo.vtt`
- Modify: `site/index.html`

- [ ] **Step 1: Capture constructed-demo stages**

Run the local workbench, load only the bundled demo, and capture requirement, confirmed criteria,
evidence matrix, Missing detail, and Blocked summary frames. Do not expose local paths or tokens.

- [ ] **Step 2: Generate deterministic video**

Use a local open-source media encoder installed only for asset production. Build five timed scenes
matching 0–5, 5–15, 15–35, 35–50, and 50–60 seconds. Burn concise captions into each scene, add
no synthetic voice, and encode H.264/AAC-compatible MP4 with no audio track.

- [ ] **Step 3: Write WebVTT captions**

Use the same segment boundaries and wording from the approved script. Add `<track kind="captions"
srclang="en" default>` to the video element.

- [ ] **Step 4: Inspect output**

Verify automated duration 59.9–60.1 seconds, 1280x720 dimensions, readable captions, required
disclosure at beginning/end, and visual correctness at 0, 30, and 59 seconds.

- [ ] **Step 5: Run media contracts and commit**

Commit as `docs: add 60-second captioned demo`.

### Task 4: Add SHA-pinned GitHub Pages deployment

**Files:**
- Create: `.github/workflows/pages.yml`
- Modify: `tests/test_repository_contracts.py`

- [ ] **Step 1: Resolve immutable Action SHAs**

Resolve the annotated release commits for `actions/checkout`, `actions/configure-pages`,
`actions/upload-pages-artifact`, and `actions/deploy-pages`. Record version comments beside each
SHA.

- [ ] **Step 2: Write the Pages workflow**

Trigger only on `push` to `main` and `workflow_dispatch`. Use the minimum Pages permissions,
concurrency cancellation, a build job that uploads `site/`, and a deploy job with the
`github-pages` environment.

- [ ] **Step 3: Extend repository contracts**

Reject floating Action tags, `pull_request_target`, `schedule`, write permissions beyond Pages,
or any artifact path outside `site/`.

- [ ] **Step 4: Verify and commit**

Run repository contracts and `git diff --check`. Commit as `ci: deploy static GitHub Pages`.

### Task 5: Browser QA and protected integration

- [ ] Serve `site/` locally and inspect desktop and mobile layouts in a real browser.
- [ ] Verify keyboard focus, all public links, video playback, captions, transcript, and no network
      requests to trackers or remote fonts.
- [ ] Run full Ruff, coverage pytest, benchmark, dependency, wheel, CLI, web health, media, and
      diff gates.
- [ ] Push one ready PR; require Python 3.11, locked-environment, `verify`, CodeQL Python/Actions,
      and Pages contract checks on the exact reviewed SHA.
- [ ] Merge, verify exact main-push CI/CodeQL, configure Pages build type to `workflow`, verify the
      deployed URL, and set the repository homepage URL.
- [ ] Do not modify issue #3 until a genuine public LinkedIn post URL exists; then edit once and
      close without a new comment.
