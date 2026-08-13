# Reproducible development environment

The public install remains v0.2.3; the current repository source is the unreleased `0.2.4.dev0`
development line. Python 3.11, Python 3.12, and Python 3.13 have current package/CLI engineering
coverage. Python 3.11 is the declared floor, Python 3.12 is the locked contributor baseline, and
Python 3.13 is exercised in protected compatibility CI and a genuine local interpreter check.
Python 3.14 is unverified pending a clean, genuine compatibility run; the current `>=3.11`
metadata must not be read as verified 3.14 support.

Dependencies are resolved by the checked-in `uv.lock`. This path uses only local and free
open-source tooling; it does not require an OpenAI or other paid LLM API.

## Create or refresh the environment

Install [uv](https://docs.astral.sh/uv/) once, then run from the repository root:

```bash
uv sync --extra dev --extra research --locked
```

`--locked` refuses to change the lock file. If dependency declarations intentionally change, run `uv lock`, inspect the resulting diff, and repeat the locked checks below.

## Opt-in R-002 engineering benchmark

Install the locked research dependency and use the four explicit local phases:

```bash
uv sync --extra dev --extra research --locked
uv run python -m scopeproof_core.evals.r002_swebench prepare --phase criteria-sources
uv run python -m scopeproof_core.evals.r002_swebench prepare --phase evidence
uv run python -m scopeproof_core.evals.r002_swebench annotate
uv run python -m scopeproof_core.evals.r002_swebench run
```

The criteria proposal requires explicit benchmark-owner confirmation before the evidence phase.
The complete candidate-label proposal requires a second explicit benchmark-owner confirmation
before `run`. Raw source material and local review bundles remain under the ignored
`.scopeproof/research/r002/` cache and must never be committed.

R-002 is public engineering research only. It does not execute target-repository code, prove
correctness, provide runtime verification, constitute customer/Alpha validation, or advance
Stage 1. Both explicit `prepare` phases are the only networked paths; `annotate` and `run` are offline.
The completed [R-002 engineering record](research/r002-swebench-verified/summary.md) reports the
frozen 20-case baseline and exact package-equivalence evidence.

## Verify the same environment

```bash
uv run ruff check .
uv run pytest
uv run scopeproof benchmark
uv run scopeproof comparison-benchmark
```

## Owner rehearsal

For a local owner/Codex rehearsal, follow the checked
[owner-rehearsal runbook](alpha/owner-rehearsal.md), beginning with
`scopeproof owner-rehearsal init`. An owner/Codex rehearsal is engineering evidence only and does
not advance Stage 1.

`scopeproof benchmark` checks deterministic acceptance-coverage behavior across the labeled local
corpus. `scopeproof comparison-benchmark` checks deterministic re-review evidence classification
across two paired previous/current cases: changed-head evidence integrity and an exact unchanged
reference. The corpus includes fail-closed ambiguous matching. Both benchmarks are deliberately
constructed engineering evidence. They do not prove correctness, do not constitute customer
validation, do not show external use, and do not advance Stage 1. Neither command executes fixture
repository code or uses a paid API.

This engineering evidence does not prove correctness, does not constitute customer validation,
and does not show external use.

Run the local workbench with:

```bash
uv run scopeproof-web --host 127.0.0.1 --port 8501
```

The Python 3.11 CI lane remains the compatibility floor. A separate locked Python 3.12 lane
verifies that the committed resolution can be recreated and runs repository contracts plus both
deterministic benchmarks. The Python 3.13 lane runs the complete suite, builds and installs a wheel,
checks dependencies and both CLI versions, runs both installed benchmarks, and requires exact
loopback workbench health before the required `verify` job. These Linux-runner checks are package
and CLI evidence, not Linux desktop evidence.

A separate hosted Windows Python 3.12 lane imports the package, CLI, and both alpha-storage
backends; runs the portable storage, process-concurrency, and no-clobber report regressions; builds
and installs the wheel; checks dependencies and both CLI versions; and runs both installed
deterministic benchmarks. It is a required dependency of `verify`. A passing lane is package,
CLI, and storage evidence only: it is not a real Windows desktop workflow, browser workflow,
screen-reader observation, accessibility-conformance result, customer signal, or Stage 1 credit.
The process-concurrency contract serializes ScopeProof writers through app-owned mutation claims.
The portable backend also requires a local filesystem with hard-link support so it can publish
without replacing an existing record; unsupported filesystems fail closed with an explicit storage
error instead of weakening no-clobber behavior.
It does not claim atomic compare-and-swap protection against a same-user process that deliberately
bypasses those claims and directly rewrites the storage directory during the final filesystem
rename; that hostile local-account scenario remains unsupported and must not be counted as proven.

## Known-good UI baseline

The checked-in lock currently resolves Streamlit 1.59.1, which passes ScopeProof's complete AppTest suite. ScopeProof requires Streamlit 1.52 or newer because the workbench relies on click-time deferred download generation to revalidate saved review truth immediately before export. During this work, Streamlit 1.57.0 exposed a testing-interface regression; that observation is why the lock is the reproducible baseline rather than a claim that every version in the supported range behaves identically. CI still installs the newest versions allowed by `pyproject.toml` in the compatibility and verification lanes so future incompatibilities remain visible without a scheduled monitor or notification workflow.
