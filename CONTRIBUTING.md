# Contributing to ScopeProof

ScopeProof is a local-first public alpha for reviewing public GitHub pull
requests against user-confirmed requirements. Contributions should preserve its
deterministic, informational, and non-blocking boundaries.

Review the [public roadmap](ROADMAP.md) before proposing broader scope. The
[changelog](CHANGELOG.md) links active development to authoritative published releases.

## Before opening a pull request

1. Keep the change focused and explain the user-confirmed requirement or bug it
   addresses. Do not invent acceptance criteria or validation results.
2. Do not include tokens, private repository links, customer data, or
   confidential source material in issues, commits, pull requests, fixtures, or
   exports.
3. For a security concern, use the repository's private vulnerability report
   instead of a public issue or pull request.
4. Do not add a paid LLM API, billing flow, private-repository ingestion, or
   repository-code execution without an explicit product decision.

## Local verification

Run the existing checks before requesting review:

```bash
python -m ruff check .
python -m pytest -q
python -m scopeproof_core.evals.runner
```

For a public GitHub smoke, preserve the PR URL, immutable head SHA, confirmed
requirements source, report, human decisions, and limitations. A green check
does not prove runtime correctness or product value.

## Pull request expectations

Use a public repository and keep ScopeProof's fork-safe, local-only, and
evidence-first behavior intact. Explain how tests cover the change and call out
any remaining reviewer or runtime verification that ScopeProof cannot perform.
