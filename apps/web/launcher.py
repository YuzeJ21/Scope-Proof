"""Launch the packaged ScopeProof Streamlit workbench."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from importlib import resources
from ipaddress import ip_address
from pathlib import Path

from scopeproof_core.version import __version__

WORKBENCH_STORAGE_ENV = "SCOPEPROOF_WORKBENCH_STORAGE_DIR"
CI_MANIFEST_DIR_ENV = "SCOPEPROOF_CI_MANIFEST_DIR"


def is_ci_loopback_host(host: str | None) -> bool:
    """Recognize the local listener addresses permitted for a configured handoff."""
    if host == "localhost":
        return True
    try:
        return ip_address(host).is_loopback
    except ValueError:
        return False


def _port(value: str) -> int:
    try:
        port = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("port must be an integer from 1..65535") from error
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError("port must be an integer from 1..65535")
    return port


def _storage_path(value: str) -> Path:
    if not value.strip() or ".." in Path(value).parts:
        raise argparse.ArgumentTypeError("storage directory must be nonempty and omit '..'")
    try:
        path = Path(value).expanduser().absolute()
    except (OSError, RuntimeError) as error:
        raise argparse.ArgumentTypeError("storage directory cannot be expanded") from error
    if not path.is_absolute():
        raise argparse.ArgumentTypeError("storage directory must resolve to an absolute path")
    return path


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Launch the packaged ScopeProof workbench")
    parser.add_argument(
        "--version",
        action="version",
        version=f"scopeproof-web {__version__}",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=_port, default=8501)
    parser.add_argument(
        "--storage-dir",
        type=_storage_path,
        help="Saved-review directory for this launch (default: ~/.scopeproof/reviews)",
    )
    parser.add_argument(
        "--ci-manifest-dir",
        type=_storage_path,
        help="Trusted local CI handoff directory (loopback launches only)",
    )
    parser.add_argument(
        "--headless",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the packaged local workbench and return Streamlit's exit code."""
    parser = _parser()
    args = parser.parse_args(argv)
    environment = os.environ.copy()
    environment.pop(CI_MANIFEST_DIR_ENV, None)
    if args.ci_manifest_dir is not None:
        if not is_ci_loopback_host(args.host):
            parser.error("--ci-manifest-dir requires a loopback host")
        environment[CI_MANIFEST_DIR_ENV] = str(args.ci_manifest_dir)
    if args.storage_dir is None:
        environment.pop(WORKBENCH_STORAGE_ENV, None)
    else:
        environment[WORKBENCH_STORAGE_ENV] = str(args.storage_dir)
    app_resource = resources.files("apps.web").joinpath("app.py")
    with resources.as_file(app_resource) as app_path:
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "streamlit",
                    "run",
                    f"--server.address={args.host}",
                    f"--server.port={args.port}",
                    f"--server.headless={str(args.headless).lower()}",
                    "--server.maxUploadSize=68",
                    "--theme.base=dark",
                    "--theme.primaryColor=#d8ff63",
                    "--theme.backgroundColor=#0d0f12",
                    "--theme.secondaryBackgroundColor=#171a1f",
                    "--theme.textColor=#f7f7f2",
                    str(app_path),
                ],
                check=False,
                env=environment,
            )
        except KeyboardInterrupt:
            return 130
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
