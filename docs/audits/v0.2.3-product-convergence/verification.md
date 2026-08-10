# ScopeProof v0.2.3 product-convergence verification

> **Historical evidence boundary:** This audit remains bound to its named commit, tree, version,
> and environment. The [current status](../../releases/v0.2.3-status-and-next-stages.md) supersedes
> unqualified present-state inferences and does not rewrite the results below.

## Evidence identity and boundary

- Date: 2026-08-02 (America/Toronto)
- Final product-code and static-site target:
  `fb74d4bbb402f4de3e2fabb56ce28c948214f8c2`
- Package, install, installed-benchmark, and workbench-health target:
  `81598899fcd85df58ab22f9212f2e8382f4a5e5f`
- Core/package target tree: `df94f15c5cbf1f8aaf67ec294992a273944abd8b`
- Mobile public-site follow-up: `01ba8fbb94b7b60b931ebf624293a3f71938cfac`
  (tree `ac916050658ed7a65b8ecaa866bc9e3aeb35bdda`)
- Favicon follow-up: `fb74d4bbb402f4de3e2fabb56ce28c948214f8c2`
  (tree `2bfca5ce214e896abfecba81afdca1da52323cfb`)
- Copyable GitHub Action source pin:
  `d553791cba83d9f756b2adce22bd814872b73ea2`
- Disposition: verified Stage 0 engineering candidate; protected integration
  remains authoritative for the final merge.
- Publication: v0.2.1 remains the published install. v0.2.3 is not tagged or
  released by this work.

Evidence is deliberately bound to the commit that was actually measured. The
package hashes remain bound to `8159889`. Full tests, coverage, Ruff,
benchmarks, repository contracts, and focused site checks were repeated after
the mobile-header and favicon follow-ups at product-code head `fb74d4b`.
Roadmap and release-audit documentation changed concurrently during the last
test pass, so this report does not claim that the worktree was clean for that
pass. This report and other documentation necessarily create a later tree;
they do not retroactively change package hashes or claim self-referential
verification. GitHub pull-request and resulting-main workflows must cover the
final integration tree.

All results here are owner-operated engineering evidence. They do not prove
target-repository runtime behavior, correctness, participant usability,
accessibility conformance, customer demand, or Stage 1 progress.

## Verified product changes

- Criteria confirmation is bound to a typed, immutable source snapshot: safe
  public source URI, optional revision, exact source-text SHA-256, ordered
  normalized-criteria digest, confirmer, and confirmation timestamp.
- New analysis, export, alpha outcome, and final acceptance require current
  matching provenance. Version 1–3 records migrate to version 4 without
  invented provenance and remain fail-closed until reconfirmed.
- Trusted gate input rejects duplicate criterion, finding, and resolution IDs;
  criterion/finding coverage mismatches; foreign resolutions; and provenance
  digest contradictions before a verdict is calculated.
- Qualifying alpha outcomes require a fully revalidated saved review whose
  public-GitHub origin, repository, PR, exact head, criteria, and provenance all
  match. Demo, fixture, research, legacy-unknown, mutated, and non-public
  origins remain ineligible. New outcomes are immutable and append-once.
- The no-network `prepare-requirements-confirmation` command calculates exact
  hashes, refuses overwrite, and avoids secret-bearing source URLs.
- The workbench and public-alpha surface use a cleaner, progressively disclosed
  hierarchy while retaining criteria confirmation, safety copy, missing
  evidence, decision history, and deterministic gates.
- The public site keeps its primary action and evidence boundary visible on
  desktop and narrow screens; the mobile header is readable and the declared
  local PNG favicon resolves without a fallback 404.

## Product-code verification

HEAD remained `fb74d4bbb402f4de3e2fabb56ce28c948214f8c2` throughout the final
product-code verification. The concurrent documentation edits are disclosed
above and final protected CI is the exact-integration authority.

| Check | Exact result |
| --- | --- |
| `uv sync --extra dev --extra research --locked` | Passed; 60 packages resolved and 55 checked. |
| `uv lock --check` | Passed. |
| `uv run ruff check .` | Passed. |
| `uv run pytest -q` | 1,885 passed and 1 intentional live test skipped. |
| Combined coverage with `--cov-fail-under=95` | 1,885 passed and 1 skipped; 8,969 statements, 438 missed, exact total 95.12%; threshold passed. |
| Repository contracts | 74 passed. |
| Constructed acceptance benchmark | 12 cases and 13 criteria; zero mismatches, zero must-have False Ready, zero false blockers, evidence-link precision 1.0. |
| Constructed comparison benchmark | Two cases and zero mismatches; 3 Added, 1 Modified, 1 Relocated, 3 Removed, and 1 Unchanged. |
| `git diff --check origin/main...HEAD` | Passed at the named product-code target; current documentation diff also passed separately. |

The benchmark cases are constructed engineering fixtures. They do not count as
public-alpha reviews or market validation.

## Built artifacts and clean installation

The artifacts below were built at clean target
`81598899fcd85df58ab22f9212f2e8382f4a5e5f` in a fresh temporary location and
installed into a fresh Python 3.12.0 virtual environment.

| Artifact | Size | SHA-256 |
| --- | ---: | --- |
| `scopeproof-0.2.3-py3-none-any.whl` | 256,479 bytes | `088670fb1d290eefd3381d9e17267d724473c0d185a79ab0d503f8821ad4a526` |
| `scopeproof-0.2.3.tar.gz` | 5,854,421 bytes | `eda85a3593eba6ad717587355bd129edf49f727ceba5b5770fcc9acdbc47dc2e` |

The wheel installed successfully. From outside the checkout:

- `scopeproof --version` returned `scopeproof 0.2.3`;
- `scopeproof-web --version` returned `scopeproof-web 0.2.3`;
- both installed benchmarks reproduced the source results;
- the installed workbench returned HTTP 200 and exact health body `ok` on a
  task-owned loopback port; and
- the server was stopped and no task listener remained.

These hashes identify internal candidate artifacts only. They are not release
assets and were not uploaded.

## Browser and product-surface verification

The workbench journey was completed in the in-app browser at 1280×720 and
390×844:

1. start a deliberately constructed demo review;
2. inspect and confirm normalized criteria;
3. run deterministic analysis;
4. inspect criterion evidence cards and the evidence matrix;
5. reach the conservative `Action required` summary; and
6. expose the Markdown, JSON, and CSV export controls.

Observed results:

- no horizontal overflow at either tested viewport;
- no browser-console warnings or errors;
- safety and candidate-evidence boundaries remained visible;
- the mobile public-site brand stayed on one line with a stacked, left-aligned
  navigation;
- the primary CTA and safety copy remained visible; and
- the declared favicon and root page each returned HTTP 200, the favicon used
  `image/png`, and a clean request log contained no `/favicon.ico` request or
  404.

Current-run screenshots:

- `/tmp/scopeproof-final-workbench-start-1280x720.jpg`
- `/tmp/scopeproof-final-workbench-evidence-cards-1280x720.jpg`
- `/tmp/scopeproof-final-workbench-evidence-matrix-390x844.jpg`
- `/tmp/scopeproof-final-workbench-summary-export-390x844.jpg`
- `/tmp/scopeproof-final-public-site-1280x720.jpg`
- `/tmp/scopeproof-final-public-site-fixed-390x844.jpg`

The favicon follow-up used exact local HTTP checks after the browser session
had finalized; the full visual journey and responsive-site checks were already
completed in the in-app browser. Screenshots and loopback HTTP responses remain
visual/runtime engineering evidence, not accessibility or participant proof.

## Unsupported or incomplete evidence

The following are not established by this verification:

- complete keyboard-only review completion;
- VoiceOver, NVDA, JAWS, or another real screen reader;
- actual 200% browser zoom;
- WCAG conformance;
- Python 3.13;
- Windows or Linux desktop flows;
- authenticated human reviewer identity;
- target-repository test, deployment, or runtime execution; or
- independent use, comprehension, repeat use, price discussion, or demand.

## Stage and release boundary

- Stage 1 remains 0/5 qualifying reviews, 0/3 independent practitioners, 0/3
  public repositories, 0/3 independently observed under-ten-minute
  completions, and 0/2 reuse-intent signals.
- Zero participant False Ready observations across zero participant cases is
  not a validated False Ready rate.
- Stages 2–4 remain gated by the roadmap's genuine-use and owner-decision
  conditions.
- No target repository code was executed.
- No account, private repository, paid API, billing resource, outreach, social
  post, email, synthetic participant, tag, GitHub Release, or release asset was
  created.
- Required `verify` and CodeQL checks plus resulting-main CI and Pages are the
  final integration evidence. A separate owner decision and fresh
  release-tree assets and checksums are still required to publish v0.2.3.
