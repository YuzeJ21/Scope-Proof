import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from scopeproof_core.criteria.confirmation import validate_requirements_confirmation


def confirmation_payload(requirements: str) -> dict:
    return {
        "requirements_sha256": hashlib.sha256(requirements.encode()).hexdigest(),
        "confirmed_by": "Demo owner",
        "confirmed_at": datetime(2026, 7, 12, tzinfo=UTC).isoformat(),
    }


def test_confirmation_record_must_match_the_exact_requirements_file(tmp_path: Path) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("Document the validation demo.\n", encoding="utf-8")
    record = tmp_path / "confirmation.json"
    record.write_text(json.dumps(confirmation_payload(requirements.read_text())), encoding="utf-8")

    confirmation = validate_requirements_confirmation(requirements, record)

    assert confirmation.confirmed_by == "Demo owner"


def test_confirmation_record_rejects_changed_requirements(tmp_path: Path) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("Original requirement.\n", encoding="utf-8")
    record = tmp_path / "confirmation.json"
    record.write_text(json.dumps(confirmation_payload(requirements.read_text())), encoding="utf-8")
    requirements.write_text("Changed requirement.\n", encoding="utf-8")

    with pytest.raises(ValueError, match="does not match"):
        validate_requirements_confirmation(requirements, record)
