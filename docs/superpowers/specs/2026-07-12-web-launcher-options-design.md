# Web Launcher Options Design

## Problem

The installed `scopeproof-web` command always launches `python -m streamlit run app.py` and
ignores every command-line argument. A clean-installed v0.1.13 smoke therefore accepted a shell
invocation containing `--host` and `--port` but still bound Streamlit to its defaults. CI did not
detect this because it configures Streamlit with environment variables.

## Decision

Give `scopeproof-web` a small, owned command-line interface:

- `--host HOST`, defaulting to `127.0.0.1`.
- `--port PORT`, defaulting to `8501` and restricted to `1..65535`.
- `--headless` and `--no-headless`, defaulting to headless mode.
- standard `--help` behavior.

The launcher converts these values to Streamlit's documented `--server.address`,
`--server.port`, and `--server.headless` options before the packaged `app.py` path. It does not
forward unknown options. The launcher continues to use the current Python interpreter, avoids a
shell, returns Streamlit's exit code, and converts `KeyboardInterrupt` to exit code 130.

Explicit CLI values take precedence over Streamlit environment variables because Streamlit
receives them as command-line options. This makes `scopeproof-web` deterministic without exposing
the full internal Streamlit CLI.

## Alternatives Considered

1. Forward all arguments unchanged. This is smaller but leaks Streamlit's internal interface and
   makes ScopeProof's supported contract unclear.
2. Document environment variables only. This preserves the bug-shaped interface and is harder for
   a first-time user than `--host` and `--port`.

## Errors and Safety

Argument parsing happens before Streamlit starts. Unknown options and invalid ports produce
Argparse's concise usage error and exit code 2, without a Python traceback. The launcher still
executes only the packaged application with the current interpreter; it never executes repository
code from a reviewed pull request.

## Verification

Regression tests must first demonstrate that v0.1.13 omits requested host and port values. After
the fix, unit tests inspect the exact subprocess argument vector, parser tests cover invalid ports,
and an installed-wheel runtime smoke must bind to a non-default loopback port and return exact
`ok` from `/_stcore/health`. Full Ruff, pytest, deterministic benchmark, and protected-main CI
remain required.

## Packaging and Documentation

README installation and health-check examples will show `scopeproof-web --host 127.0.0.1 --port
8501`. Because this fixes the installed public entry point, the package version advances to
`0.1.14`; a release is justified only after the exact merged-main commit and public assets pass the
same clean-install runtime check.
