# ScopeProof Beta-Entry Hardening Design

## Context

ScopeProof is an engineering-complete public alpha with protected CI, CodeQL, immutable Action
pins, 718 passing tests, and a 12-case deterministic benchmark. The remaining repository-owned
beta-entry gaps are not product features:

- the public repository intentionally has no open-source license but does not state that policy;
- CI runs the full suite but does not enforce a coverage floor;
- `verify` is required on protected `main`, while CodeQL is green but not required;
- more than 120 specifications and plans are useful audit history but lack a contributor-facing
  index.

This slice addresses only those ScopeProof gaps. It does not touch Stock-Analysis.

## Approved direction

Use a conservative public-evaluation posture rather than granting an open-source license.
GitHub documents that, without a license, default copyright law applies and the copyright holder
retains rights. ScopeProof will make that existing posture explicit without adding a recognized
open-source license or implying legal advice.

The implementation will add `USE_POLICY.md` stating:

- the repository is intentionally published without an open-source license;
- public visibility permits viewing and GitHub-platform actions only to the extent supplied by
  GitHub's Terms of Service or applicable law;
- no additional permission is granted to use, copy, modify, distribute, sublicense, or create
  derivative works;
- evaluation access does not create a warranty, service commitment, or correctness claim;
- permission requests must go to the repository owner.

README and CONTRIBUTING will link the policy. ROADMAP's software-license decision will become a
completed explicit evaluation-only decision, while keeping PyPI publication and active outside
contribution invitations gated on a future owner decision.

## Coverage gate

A clean local probe against `scopeproof_core` and `apps` measured 97% statement coverage:
2,605 statements with 82 missed. CI will enforce a 95% floor on Python 3.12 using `pytest-cov`.
The 2-point margin prevents harmless interpreter or platform differences from making the threshold
brittle while still detecting a meaningful untested regression.

Implementation details:

- add `pytest-cov>=6,<7` to the development dependency set;
- replace the Python 3.12 plain pytest step with
  `python -m pytest --cov=scopeproof_core --cov=apps --cov-report=term-missing:skip-covered --cov-fail-under=95 -q`;
- retain the full plain test suite on Python 3.11 so the minimum-version compatibility job remains
  independent of coverage-tool behavior;
- do not upload coverage to an external service or create a coverage artifact;
- ignore local `.coverage` files.

Coverage is a regression signal, not product-correctness or external-validation evidence.

## Required CodeQL protection

After the repository changes merge and the final main checks succeed, protected `main` will require
both `verify` and the existing GitHub code-scanning aggregate context `CodeQL`, with strict status
checks preserved. No review-count requirement is added because the repository remains a
single-owner alpha and a second-person approval requirement would make normal maintenance
impossible.

The branch-protection change will be applied through the GitHub API only after confirming the
`CodeQL` context has passed on the pull request and merged main commit. The setting will be read back
and compared with the intended contexts.

## Internal documentation index

Add `docs/superpowers/README.md` as a navigation and provenance boundary:

- specs describe accepted historical designs;
- plans describe intended implementation steps and may contain completed checklist history;
- neither folder is current product status, runtime evidence, or adoption evidence;
- `ROADMAP.md`, `README.md`, `CHANGELOG.md`, and current GitHub checks remain the public truth
  sources;
- contributors should open only the document relevant to the changed behavior rather than treating
  the archive as a sequential manual.

CONTRIBUTING will link this index.

## Explicit exclusions

- No paid API, LLM, hosting, account, organization, private repository, or billing work.
- No Dependabot configuration, scheduled workflow, automated outreach, or notification bot.
- No required second-person approval.
- No PyPI publication or release solely for policy, CI, and navigation changes.
- No generic security scanner, auto-fix feature, or untrusted repository-code execution.
- No refactor of `apps/web/app.py`, schemas, exporters, or tests without a reproducible defect.
- No external-use, customer, beta, or correctness claim.

## Acceptance criteria

1. Public docs state and link the evaluation-only, no-open-source-license posture without a
   `LICENSE` file or SPDX license claim.
2. Python 3.12 CI enforces at least 95% statement coverage over `scopeproof_core` and `apps` using
   the full test suite; Python 3.11 compatibility remains unchanged.
3. Internal design history has a clear index that distinguishes archive material from current
   product truth and evidence.
4. Repository contract tests fail before each repository-file change and pass afterward.
5. Ruff, all tests, coverage, the deterministic benchmark, dependency checks, wheel smoke, and
   `git diff --check` pass.
6. The pull request passes `verify`, Python 3.11 compatibility, and CodeQL before merge.
7. Protected `main` requires exactly the intended `verify` and `CodeQL` contexts after merge.
8. No release, scheduled task, bot comment, dependency-update automation, or paid service is
   created.
