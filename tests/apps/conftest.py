"""Keep Streamlit AppTest persistence away from the user's local records."""

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolate_app_test_storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
