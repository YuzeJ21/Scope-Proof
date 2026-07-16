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
```

Run the local workbench with:

```bash
uv run scopeproof-web --host 127.0.0.1 --port 8501
```

The Python 3.11 CI lane remains the compatibility floor. A separate locked Python 3.12 lane verifies that the committed resolution can be recreated and runs repository contracts plus the deterministic benchmark before the required `verify` job.
