from pathlib import Path

from scopeproof_core.alpha.rehearsal_storage import default_alpha_rehearsal_directory
from scopeproof_core.alpha.storage import default_alpha_case_directory
from scopeproof_core.storage.json_store import default_local_review_directory


def test_app_test_defaults_are_confined_to_own_temporary_root(tmp_path: Path) -> None:
    for directory in (
        default_local_review_directory(),
        default_alpha_case_directory(),
        default_alpha_rehearsal_directory(),
    ):
        assert directory.is_relative_to(tmp_path)
