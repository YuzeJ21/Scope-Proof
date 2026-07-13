"""Launch the packaged ScopeProof Streamlit workbench."""

from __future__ import annotations

import argparse
import subprocess
import sys
from importlib import resources


def _port(value: str) -> int:
    try:
        port = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("port must be an integer from 1..65535") from error
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError("port must be an integer from 1..65535")
    return port


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Launch the packaged ScopeProof workbench")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=_port, default=8501)
    parser.add_argument(
        "--headless",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the packaged local workbench and return Streamlit's exit code."""
    args = _parser().parse_args(argv)
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
                    str(app_path),
                ],
                check=False,
            )
        except KeyboardInterrupt:
            return 130
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
