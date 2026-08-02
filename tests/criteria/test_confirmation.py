import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from scopeproof_core.criteria.confirmation import (
    build_criteria_source_provenance,
    canonical_criteria_sha256,
    source_text_sha256,
    validate_requirements_confirmation,
)
from scopeproof_core.schemas.models import Criterion


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


@pytest.mark.parametrize("confirmed_by", ["", "   ", "\t\n"])
def test_confirmation_record_rejects_blank_confirmer(
    tmp_path: Path, confirmed_by: str
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("Document the validation demo.\n", encoding="utf-8")
    payload = confirmation_payload(requirements.read_text())
    payload["confirmed_by"] = confirmed_by
    record = tmp_path / "confirmation.json"
    record.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="confirmed_by must contain non-whitespace text"):
        validate_requirements_confirmation(requirements, record)


def test_confirmation_record_preserves_valid_confirmer_text(tmp_path: Path) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("Document the validation demo.\n", encoding="utf-8")
    payload = confirmation_payload(requirements.read_text())
    payload["confirmed_by"] = "  Demo owner  "
    record = tmp_path / "confirmation.json"
    record.write_text(json.dumps(payload), encoding="utf-8")

    confirmation = validate_requirements_confirmation(requirements, record)

    assert confirmation.confirmed_by == "  Demo owner  "


def test_criteria_source_provenance_hashes_exact_utf8_source_and_canonical_criteria() -> None:
    source_text = "Export the café list.\n"
    criteria = [
        Criterion(
            criterion_id="AC-02",
            text="Show a clear export error",
            source_span=None,
        ),
        Criterion(
            criterion_id="AC-01",
            text="Export the filtered list as CSV",
            source_span="requirements:1",
        ),
    ]

    provenance = build_criteria_source_provenance(
        source_uri=" https://example.test/requirements ",
        source_revision="  revision-42  ",
        source_text=source_text,
        criteria=criteria,
        confirmed_by="  Product owner  ",
        confirmed_at=datetime(2026, 8, 2, 12, 30, tzinfo=UTC),
    )

    canonical_payload = [criterion.model_dump(mode="json") for criterion in criteria]
    expected_criteria_digest = hashlib.sha256(
        json.dumps(
            canonical_payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()

    assert provenance.source_uri == "https://example.test/requirements"
    assert provenance.source_revision == "revision-42"
    assert provenance.confirmed_by == "Product owner"
    assert provenance.source_text_sha256 == hashlib.sha256(source_text.encode("utf-8")).hexdigest()
    assert provenance.normalized_criteria_sha256 == expected_criteria_digest
    assert source_text_sha256(source_text) == provenance.source_text_sha256
    assert canonical_criteria_sha256(criteria) == provenance.normalized_criteria_sha256


def test_criteria_source_provenance_preserves_criterion_order_and_explicit_none_fields() -> None:
    first = Criterion(criterion_id="AC-01", text="Export CSV", source_span=None)
    second = Criterion(criterion_id="AC-02", text="Show an error", source_span=None)

    assert canonical_criteria_sha256([first, second]) == (
        "af775d21a172014230132c7f2f7662df9ae69915e998251856778456e1cefd3b"
    )
    assert canonical_criteria_sha256([second, first]) != canonical_criteria_sha256(
        [first, second]
    )
