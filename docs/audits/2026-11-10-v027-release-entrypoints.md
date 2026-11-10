# Published v0.2.7 entry-point alignment

Observed 2026-11-10. This assessment records source preparation and bounded automated previews.
The enclosing PR and manual Pages run record later integration and publication separately.
It is not a customer review, runtime-correctness claim or Stage 3 milestone.

## Baseline and correction

Live main was clean at `e099679ed63309716a7ce4726557ef794bfd5c80`, after PR #278, with
successful CI, CodeQL and base-advance runs and no open PRs. The public non-draft v0.2.7 release
identified that same source and the verified wheel, source archive and checksum manifest.
Its release-source CI `42547822181` recorded 4,888 tests, 38 intentional skips and 95.5192%
coverage. The Release entry records anonymous downloads and fresh public-archive installations
on macOS/Python 3.11; Windows CI is separate evidence.

The README, evaluation guide and roadmap still made v0.2.7 publication conditional. The live
website advertised published v0.2.6 and unpublished `0.2.7.dev0`. This update makes published
v0.2.7 the default evaluation download, closes final distribution, and separates its immutable
source from the later documentation/site revision. Current-source headers in linked operating
documents follow the same distinction. The existing page layout, workflows and media remain.

The existing immutable-release contract rejected tracked changes reusing final `0.2.7`.
Development identity therefore advances to unpublished `0.2.8.dev0`, with v0.2.7 added to the
existing final-version guard cases. Committed-tree, tracked-tree and untracked-input checks
remain intact. This changes the current reader/core fingerprint through `version.py`; it does
not change product behavior, historical producer fingerprints or published artifacts.
The dynamic editable entry in `uv.lock` needs no version/dependency change.

## Automated preparation evidence

- The two existing current-release/site contracts failed against stale guidance, then passed
  after alignment. Repository contracts plus build-identity checks passed: 156 tests.
- `ruff check .`, `git diff --check` and locked environment synchronization passed.
- The deterministic benchmark passed 12 cases/13 criteria without mismatches, False Ready or
  false-blocker results; the comparison benchmark passed both constructed cases. Frozen R-002
  inputs/results and the actual released-writer corpus remain unchanged.
- Local Chromium captured five index sizes (1365×768, 1440×900, 768×1024, 390×844 and 320×568)
  and the 390-pixel transcript. Six captures had no horizontal overflow, HTTP or browser errors.
  Sixteen local/repository links and keyboard skip navigation passed. Desktop release actions
  and evidence boundaries remained above the fold at the checked desktop sizes.
- Preview manifests are Pydantic-validated and bind source HEAD, dirty status and file hashes.
  They identify pre-commit working-tree previews, not exact-head hosted or public verification.
  Preview servers stopped after capture. Rendering checks do not establish accessibility conformance.

Private recipes, before/after captures, logs and later validated publication evidence are kept
under `~/.codex/artifacts/scopeproof-v027-entrypoints-2026-11-10/`. Full-suite/coverage results,
independent engineering findings, exact PR head, resulting main and publication identities are
recorded in that packet and the PR/workflow when observed; the source assessment does not predict them.

## Publication and preserved boundaries

The owner explicitly authorized review, merge after green checks, and site publication.
The unchanged Pages workflow remains manual-only. After resulting-main checks pass, dispatch
the approved revision and verify the actual run/deployment source, all public file bytes,
links, anonymous v0.2.7 downloads/checksums and bounded browser/media behavior.
The release source remains `e099679ed63309716a7ce4726557ef794bfd5c80` even when main and Pages advance.

Historical packets, the actual v0.2.6 sample producer/input/ZIP/HTML, native fixtures, captioned
media, benchmark expectations, policy, schemas and gate decisions are preserved. No package
publication, target-code execution, participant contact, personal testing or qualifying review
is included. Stage 1 stays closed with all external counts zero; Stage 3 stays dormant pending
genuine independent use and separate authorization. No additional feature or release follows automatically.
