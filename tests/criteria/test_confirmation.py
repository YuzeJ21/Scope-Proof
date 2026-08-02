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
    criteria = [Criterion(criterion_id="AC-01", text=requirements.strip())]
    return {
        "source_uri": "https://example.test/requirements",
        "source_revision": "revision-42",
        "source_text_sha256": source_text_sha256(requirements),
        "normalized_criteria_sha256": canonical_criteria_sha256(criteria),
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
    assert confirmation.source_uri == "https://example.test/requirements"
    assert confirmation.source_revision == "revision-42"


def test_confirmation_hashes_exact_crlf_utf8_bytes_without_newline_translation(
    tmp_path: Path,
) -> None:
    requirements = tmp_path / "requirements.txt"
    raw = b"First requirement.\r\nSecond requirement.\r\n"
    requirements.write_bytes(raw)
    source_text = raw.decode("utf-8")
    payload = confirmation_payload(source_text)
    payload["normalized_criteria_sha256"] = canonical_criteria_sha256(
        [
            Criterion(criterion_id="AC-01", text="First requirement."),
            Criterion(criterion_id="AC-02", text="Second requirement."),
        ]
    )
    record = tmp_path / "confirmation.json"
    record.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    confirmation = validate_requirements_confirmation(requirements, record)

    assert confirmation.source_text_sha256 == hashlib.sha256(raw).hexdigest()


def test_confirmation_rejects_an_empty_normalized_criterion_set() -> None:
    with pytest.raises(ValueError, match="at least one criterion"):
        build_criteria_source_provenance(
            source_uri="https://example.test/requirements",
            source_text="Requirements exist but no criterion was selected.",
            criteria=[],
            confirmed_by="Product owner",
            confirmed_at=datetime(2026, 8, 2, tzinfo=UTC),
        )


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

    assert confirmation.confirmed_by == "Demo owner"


def test_confirmation_record_rejects_reordered_normalized_criteria(tmp_path: Path) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("First requirement.\nSecond requirement.\n", encoding="utf-8")
    payload = confirmation_payload(requirements.read_text())
    payload["normalized_criteria_sha256"] = canonical_criteria_sha256(
        [
            Criterion(criterion_id="AC-01", text="Second requirement."),
            Criterion(criterion_id="AC-02", text="First requirement."),
        ]
    )
    record = tmp_path / "confirmation.json"
    record.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="normalized criteria"):
        validate_requirements_confirmation(requirements, record)


def test_confirmation_record_rejects_legacy_hash_only_shape(tmp_path: Path) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("Document the validation demo.\n", encoding="utf-8")
    record = tmp_path / "confirmation.json"
    record.write_text(
        json.dumps(
            {
                "requirements_sha256": source_text_sha256(requirements.read_text()),
                "confirmed_by": "Demo owner",
                "confirmed_at": "2026-07-12T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="source_uri"):
        validate_requirements_confirmation(requirements, record)


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
