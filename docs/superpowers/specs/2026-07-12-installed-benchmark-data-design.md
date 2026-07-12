# Installed Benchmark Data Design

## Problem

The `scopeproof` wheel installs and exposes its CLI, but `scopeproof benchmark` fails from a clean environment because `evals/fixtures` and `evals/labels` are not included in the wheel. The command therefore contradicts the package's advertised installed CLI behavior.

## Design

Keep the benchmark corpus in its existing repository-level `evals` directory and use Hatch's wheel `force-include` mapping to place that directory at `evals` in the wheel. The existing runner deliberately resolves the corpus relative to the installed site-packages root, so no runtime code or path behavior needs to change.

Add a repository contract that parses `pyproject.toml`, requires the exact `evals = "evals"` force-include mapping, and confirms both source corpus directories contain JSON. Verify the real artifact separately by rebuilding the wheel, inspecting its archive, installing it into a fresh temporary environment, and running the installed benchmark.

## Alternatives

- Move the corpus under `scopeproof_core`. This would work but would churn all fixture paths and mix executable code with a sizeable labelled-data corpus.
- Remove or disable the installed benchmark command. This would weaken reproducibility and contradict the documented CLI.
- Download benchmark data at runtime. This would violate the local-first, deterministic, offline benchmark boundary.

## Boundaries

The change adds no dependency, network call, paid service, generated evidence, or new benchmark label. It does not alter findings, gates, metrics, or benchmark expectations.
