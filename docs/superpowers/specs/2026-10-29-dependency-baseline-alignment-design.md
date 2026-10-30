# Maintained dependency declaration alignment

Baseline: clean main `7dda0eeccedf56e23185399e46ab2459aba51bc0`, merged PR #219.
Public v0.2.4 is unchanged; current source remains unreleased `0.2.5.dev0`.

## Supported change

Align current package requirements with the combination already verified on Python 3.11.15:
HTTPX `>=0.27,<1`, Pydantic `>=2.13.4,<3`, Streamlit `>=1.66.1,<2`, Pillow `>=13,<14`.
Pydantic 2.13.4 is a maintained verified floor, not a proven earliest working version. Retain
upper bounds and all existing optional dependencies. Streamlit 1.66.1 itself allows Pillow from
9.2.0; an explicit direct Pillow floor is required to exclude retained older installations.

Choose the verified floors rather than bisecting older versions or pinning the entire runtime.
Update root lock metadata while preserving every resolved package version. No application,
engine, schema, gate, fixture, workflow or frozen R-002 change is needed. Preserve the dated old
floor failures and public wheel identity; source metadata cannot repair already published bytes.

## Verification and finish line

Exercise actual requirement admission at source, lock and installed-distribution boundaries:
accept exact verified floors, exclude known older combinations and incompatible major versions.
Inspect the built wheel's requirements and use a real resolver to reject conflicting old pins.
Install all four exact floors in one isolated Python 3.11 transaction, require package identity
and `pip check`, and run full source tests plus installed CLI/benchmarks and packaged browser.
Preserve existing full covered suite, unrounded 95% threshold, lint, protected Python/Windows CI,
CodeQL and independent automated review. Merge with the passing exact head and verify main.

The owner delegated implementation and integration and declines personal testing/qualifying
reviews. Proceed without routine design questions. No new matrix, feature, generic scanning,
target code execution, release, deployment, outreach or Stage 3 advancement. Arbitrary future
dependency combinations, Windows desktop/accessibility and genuine independent use remain
unverified. Stop after this bounded metadata correction and passing integration.
