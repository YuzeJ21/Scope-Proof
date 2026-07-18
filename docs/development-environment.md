# Reproducible development environment

ScopeProof supports Python 3.11 and newer. The contributor baseline is Python 3.12 with dependencies resolved by the checked-in `uv.lock`. This path uses only local and free open-source tooling; it does not require an OpenAI or other paid LLM API.

## Create or refresh the environment

Install [uv](https://docs.astral.sh/uv/) once, then run from the repository root:

```bash
uv sync --extra dev --locked
```

`--locked` refuses to change the lock file. If dependency declarations intentionally change, run `uv lock`, inspect the resulting diff, and repeat the locked checks below.

## Verify the same environment

```bash
uv run ruff check .
uv run pytest
uv run scopeproof benchmark
uv run scopeproof comparison-benchmark
```

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

The Python 3.11 CI lane remains the compatibility floor. A separate locked Python 3.12 lane verifies that the committed resolution can be recreated and runs repository contracts plus the deterministic benchmark before the required `verify` job.

## Known-good UI baseline

The checked-in lock currently resolves Streamlit 1.59.2, which passes ScopeProof's complete AppTest suite. During this work, Streamlit 1.57.0 exposed a testing-interface regression; that observation is why the lock is the reproducible baseline rather than a claim that every version in the broad supported range behaves identically. CI still installs the newest versions allowed by `pyproject.toml` in the compatibility and verification lanes so future incompatibilities remain visible without a scheduled monitor or notification workflow.
