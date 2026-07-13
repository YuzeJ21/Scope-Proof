"""Launch the packaged ScopeProof Streamlit workbench."""

from __future__ import annotations

import subprocess
import sys
from importlib import resources


def main() -> int:
    """Run the packaged local workbench and return Streamlit's exit code."""
    app_resource = resources.files("apps.web").joinpath("app.py")
    with resources.as_file(app_resource) as app_path:
        try:
            result = subprocess.run(
                [sys.executable, "-m", "streamlit", "run", str(app_path)],
                check=False,
            )
        except KeyboardInterrupt:
            return 130
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
