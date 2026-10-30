# Dependency declaration alignment — 2026-10-29

## Baseline and scope

At start, PR #219 was merged and main `7dda0eeccedf56e23185399e46ab2459aba51bc0` was clean with
passing CI, CodeQL and base-advance checks. The owner authorized declaration alignment, independent
automated review and guarded merge, and declined personal testing and qualifying reviews.

The [preceding assessment](2026-10-29-runtime-dependency-floor.md) remains a dated record of actual
public-wheel and source results. Its old Pydantic 2.8 failures and partial Streamlit 1.53 browser
observation are preserved. This follow-up changes current unreleased `0.2.5.dev0` distribution
metadata; it does not repair public v0.2.4 bytes, metadata, tag or assets in place.

| Runtime dependency | Current source contract | Reason |
| --- | --- | --- |
| HTTPX | `>=0.27,<1` | Retain the already verified floor. |
| Pydantic | `>=2.13.4,<3` | Use the verified maintained baseline; the old floor failed R-002 strict JSON validation. |
| Streamlit | `>=1.66.1,<2` | Use the verified UI baseline that permits Pillow 13. |
| Pillow | `>=13,<14`, direct | Streamlit itself permits Pillow from 9.2; its floor alone would admit retained older Pillow. |

These are maintained verified choices, not a claim that every earlier version fails or every
future permitted resolution works. No version bisection or new standing matrix was added.

All resolved lock versions and every non-root package entry remain unchanged. uv 0.11.29, the
existing pinned CI tool, regenerated root requirements and normalized lock format revision 5 to 3.
That format field is not a package version. Locked synchronization and protected CI must accept
the generated file; it must not cause a hidden dependency upgrade.

## Verification contract

Admission regressions cover source, root lock metadata and the installed distribution: accept
each exact verified floor and exclude known older pins and incompatible major versions. Before
the change, 15 cases failed and 21 passed: the old Pydantic and Streamlit were admitted, and an
explicit Pillow requirement was missing. With updated declarations and installed metadata, all
36 admission cases and the existing repository/CI contracts passed (181 tests total).

The candidate wheel must expose the same requirements and reject old Pydantic, Streamlit and
Pillow pins through the real resolver. An external genuine Python 3.11 environment installs all
four exact floors together, verifies import identity and dependencies, and exercises the full
source suite plus installed CLI/benchmarks and constructed workbench behavior. Exact candidate
hashes, dependency manifests, commands and outcomes are retained with the PR verification record;
full covered suite, unrounded 95% floor, lint, Python/Windows compatibility and packaged-browser
checks remain required. Independent review and exact-head CI precede guarded merge and main checks.

No application, core, evidence schema, gate, criteria confirmation, reviewer control, workflow,
fixture or frozen R-002 input/result changed. All observations are automated engineering evidence
with zero genuine independent-use credit. Public v0.2.4 still needs the explicit installation
constraints in the README and retains its documented browser boundary issue. No release,
deployment, outreach, personal testing, qualifying review, accessibility-conformance claim or
Stage 3 advancement follows. Stop after passing integration and return to bounded maintenance.
