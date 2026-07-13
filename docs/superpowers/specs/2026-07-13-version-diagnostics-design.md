# Installed Version Diagnostics Design

## Problem

ScopeProof now has one truthful package and review version source, but neither installed command can
report it. `scopeproof --version` exits with code 2 because the parser requires a subcommand, and
`scopeproof-web --version` exits with code 2 because the launcher does not recognize the option.

This blocks a basic first-use and support diagnostic: a user cannot distinguish the published
v0.1.14 wheel, an older editable installation, or the current `0.1.15.dev0` development build before
running a review or starting Streamlit.

## Decision

Add conventional argparse `--version` actions to both public parsers. Each command prints its own
program name followed by `scopeproof_core.version.__version__` and exits successfully.

- `scopeproof --version` prints `scopeproof 0.1.15.dev0` on the current development line.
- `scopeproof-web --version` prints `scopeproof-web 0.1.15.dev0` without launching Streamlit.
- Installed release wheels will print their final release version from the same source.

## Components and Boundaries

- `scopeproof_core.cli` imports `__version__` and registers the main CLI version action before the
  required subparser group.
- `apps.web.launcher` imports the same constant and registers the launcher version action before
  parsing host, port, or headless options.
- No distribution metadata lookup, repository-file read, network call, or subprocess is required.
- `scopeproof_core` remains independent of Streamlit; the launcher depends on the core version, not
  the reverse.

## Error and Compatibility Behavior

- `--version` ignores the need for a command because argparse handles the action before validating
  required subparsers.
- `scopeproof-web --version` returns before resolving the packaged app or invoking Streamlit.
- Existing help, commands, launcher arguments, exit codes, review schemas, and saved records remain
  unchanged.
- Extra arguments after `--version` follow argparse's standard immediate-exit behavior.

## Verification

- Parser-level tests prove exact output and exit code 0 for both entrypoints.
- A launcher test proves no subprocess is invoked for `--version`.
- Repository contract coverage requires installed-wheel smoke to execute both commands.
- A clean-built, clean-installed wheel must report `0.1.15.dev0` through both console scripts.
- Ruff, the full offline suite, deterministic benchmark, and diff hygiene remain green.

This bounded diagnostic is included in the next release batch; it does not justify a standalone
release, issue update, or other notification-generating activity.
