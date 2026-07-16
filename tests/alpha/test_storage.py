import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from scopeproof_core.alpha.models import ParticipantRole
from scopeproof_core.alpha.service import initialize_alpha_case
from scopeproof_core.alpha.storage import JsonAlphaCaseStore, UnsafeAlphaCaseStore


def alpha_case():
    return initialize_alpha_case(
        public_pr_url="https://github.com/acme/repo/pull/7",
        requirements_source_url="https://github.com/acme/repo/issues/6",
        participant_role=ParticipantRole.ENGINEERING,
        source_owner_confirmed=True,
        no_confidential_information=True,
        confirmed_criteria=["Export CSV"],
    )


def test_alpha_case_round_trips_as_validated_json(tmp_path: Path) -> None:
    record = alpha_case()
    store = JsonAlphaCaseStore(tmp_path)

    path = store.save(record)

    assert store.load(record.case_id) == record
    assert path.name == f"{record.case_id}.json"
    assert store.list_case_ids() == [record.case_id]


def test_alpha_case_save_refuses_silent_overwrite(tmp_path: Path) -> None:
    record = alpha_case()
    store = JsonAlphaCaseStore(tmp_path)
    store.save(record)

    with pytest.raises(FileExistsError):
        store.save(record)


def test_alpha_case_update_requires_existing_same_case(tmp_path: Path) -> None:
    record = alpha_case()
    store = JsonAlphaCaseStore(tmp_path)

    with pytest.raises(FileNotFoundError):
        store.update(record)

    store.save(record)
    replacement = alpha_case()
    replacement = replacement.model_copy(update={"case_id": record.case_id})
    assert store.update(replacement) == tmp_path / f"{record.case_id}.json"
    assert store.load(record.case_id) == replacement


@pytest.mark.parametrize("case_id", ["../escape", "alpha-not-a-uuid", "/tmp/case"])
def test_alpha_store_rejects_unsafe_case_ids(tmp_path: Path, case_id: str) -> None:
    with pytest.raises(ValueError):
        JsonAlphaCaseStore(tmp_path).load(case_id)


def test_alpha_store_rejects_symlink_root(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "cases"
    link.symlink_to(target, target_is_directory=True)

    with pytest.raises(UnsafeAlphaCaseStore):
        JsonAlphaCaseStore(link).list_case_ids()


def test_alpha_store_revalidates_loaded_payload(tmp_path: Path) -> None:
    record = alpha_case()
    store = JsonAlphaCaseStore(tmp_path)
    path = store.save(record)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["no_confidential_information"] = False
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValidationError):
        store.load(record.case_id)
