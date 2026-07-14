# Post-v0.1.18 Development Version Plan

**Goal:** Distinguish unreleased post-v0.1.18 source builds and review provenance
from the verified public v0.1.18 artifact.

1. Change the single-version repository contract first from `0.1.18` to
   `0.1.19.dev0`; run it and require RED.
2. Change only `scopeproof_core/version.py` to `0.1.19.dev0`; rerun the contract
   and direct metadata/new-review identity probes and require GREEN.
3. Run Ruff, full pytest, deterministic benchmark, archived-wheel install,
   version/CLI/new-review identity, and loopback workbench health.
4. Independently review the branch; push one ready PR; require both `verify`
   checks and CodeQL; merge and verify exact main.
5. Do not update README release URLs, Action pin, tag, or release.
