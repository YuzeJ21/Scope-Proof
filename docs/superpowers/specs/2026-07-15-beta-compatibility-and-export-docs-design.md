# Beta Compatibility and Export Documentation Design

## Context

ScopeProof declares Python `>=3.11`, while the protected CI workflow currently executes only on
Python 3.12. The current green check therefore proves the primary development runtime, but it does
not prove the package's declared minimum. The project also implements and tests HTML exports, yet
the README's public workflow, architecture diagram, and repository layout name only Markdown,
JSON, and CSV.

Both gaps are independent of unavailable customer evidence. They can be closed without inventing
a user, changing evidence semantics, adding a paid service, or publishing another release.

## Decision

Add one narrow `compatibility-python-311` CI job using the same immutable checkout and Python setup
Actions as the protected `verify` job. The compatibility job will install the editable development
package, run the complete offline test suite and deterministic benchmark, build and install a wheel,
and exercise both CLI version commands. It will not duplicate the Streamlit HTTP smoke. The existing
`verify` job will depend on this job, preserving the required check name while ensuring a Python
3.11 failure prevents `verify` from succeeding.

Update the README so every public export inventory consistently includes HTML. Add repository
contract tests before changing the workflow and README so both gaps are observed as focused failures
and remain regression-protected.

## Alternatives considered

- Duplicate the full `verify` job through a two-version matrix: rejected because it repeats the
  installed Streamlit HTTP smoke and makes the required check name more difficult to keep stable.
- Add a narrow Python 3.11 compatibility job: selected because it proves the declared minimum while
  preserving the existing Python 3.12 product smoke and protected `verify` context.
- Change `requires-python` to `>=3.12`: rejected because no incompatibility evidence justifies
  dropping Python 3.11 support.
- Correct documentation without a contract: rejected because the same public-capability drift could
  recur silently.

## CI contract

- `.github/workflows/ci.yml` retains the job id and required status context `verify`.
- `compatibility-python-311` uses Python 3.11 on `ubuntu-latest` with immutable third-party Action
  revisions.
- The compatibility job runs editable installation, the complete offline test suite, the
  deterministic benchmark, wheel build and installation, `scopeproof --version`, and
  `scopeproof-web --version`.
- `verify` declares `needs: compatibility-python-311` and retains the current Python 3.12 Ruff,
  test, benchmark, installed-wheel, CLI, and loopback HTTP smoke steps.
- No larger runner, private repository, hosted service, or billing configuration is introduced.

## Documentation contract

- The one-command report help states that `.md`, `.json`, `.csv`, and `.html` are supported.
- The repeat-export example shows `--format html` as an available format without removing the
  existing Markdown example.
- The architecture output and repository layout list HTML alongside Markdown, JSON, and CSV.
- HTML remains a deterministic local export. It is not presented as runtime, correctness, customer,
  or adoption evidence.

## Verification

1. Add focused repository-contract assertions and run them to observe failures against the current
   one-version workflow and incomplete README inventory.
2. Update the workflow and README, then rerun the focused contracts.
3. Run Ruff, the complete offline suite, deterministic benchmark, `pip check`, and
   `git diff --check`.
4. Build the wheel and exercise current-environment package identity and both CLI version commands.
5. Publish through one protected `codex/*` PR and merge only after the required `verify` and CodeQL
   checks succeed.

## Boundaries

No evidence rule, schema, gate, retrieval behavior, lifecycle, storage behavior, runtime-evidence
claim, user, customer, license, release, PyPI publication, private-repository feature, fork test,
paid API, LLM API, billing, organization, second account, telemetry, recurring monitor, issue
comment, label, or manually sent email is created.
