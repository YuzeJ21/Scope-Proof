"""Independent CLI history safety checks against trusted constructed local records."""

from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from importlib import import_module
from threading import Event

import pytest

from scopeproof_core.cli import main
from scopeproof_core.storage.json_store import JsonReviewStore
from tests.reviews.test_historical_analysis import history_only_state


def _module():
    return import_module("scopeproof_core.cli_history")


def _saved(tmp_path):
    state = history_only_state()
    store = JsonReviewStore(tmp_path / "records")
    path = store.save(state)
    fingerprint = sha256(store.load(state.review.review_id).model_dump_json().encode()).hexdigest()
    return state, store, path, fingerprint


def _export_args(state, store, fingerprint, *, output=None, position="2", format="json"):
    args = [
        "export-history", state.review.review_id,
        "--history-position", position,
        "--expected-state-fingerprint", fingerprint,
        "--storage-dir", str(store.directory), "--format", format,
    ]
    if output is not None:
        args.extend(["--output", str(output)])
    return args


def _assert_refused(args, capsys):
    with pytest.raises(SystemExit) as error:
        main(args)
    assert error.value.code == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "invalid choice: 'export-history'" not in captured.err
    assert "invalid choice: 'history'" not in captured.err
    assert "Traceback" not in captured.err
    return captured.err


def test_pending_current_revision_can_export_explicit_retained_history(tmp_path, capsys):
    """A CLI limited to current bundles would lose valid retained handoff."""
    state, store, path, fingerprint = _saved(tmp_path)
    before = path.read_bytes()
    assert state.bundle is None and not state.criteria_revision.confirmed
    assert main(_export_args(state, store, fingerprint)) == 0
    output = capsys.readouterr().out
    assert '"report_kind": "scopeproof_historical_analysis"' in output
    assert '"history_index": 1' in output
    assert path.read_bytes() == before


@pytest.mark.parametrize("position", [True, False, 0, -1, 1.0, "1", None])
def test_request_model_never_coerces_history_position(position):
    """Strict schema validation must reject bools and numeric-looking inputs."""
    with pytest.raises(ValueError):
        _module().HistoricalExportRequest(
            review_id="constructed-record", history_position=position,
            expected_state_fingerprint="a" * 64,
        )


@pytest.mark.parametrize("fingerprint", ["A" * 64, "g" * 64, "a" * 63, "a" * 65,
                                         " a" + "a" * 63, 1, None])
def test_request_model_requires_exact_lowercase_sha256(fingerprint):
    with pytest.raises(ValueError):
        _module().HistoricalExportRequest(
            review_id="constructed-record", history_position=1,
            expected_state_fingerprint=fingerprint,
        )


@pytest.mark.parametrize("field,value", [
    ("--history-position", "0"), ("--history-position", "-1"),
    ("--history-position", "1.0"), ("--history-position", "true"),
    ("--expected-state-fingerprint", "A" * 64),
    ("--expected-state-fingerprint", "b" * 63),
])
def test_invalid_selection_is_rejected_before_record_read(tmp_path, capsys, monkeypatch,
                                                          field, value):
    """Invalid selection must not open the record before validating the request."""
    def unexpected_read(*_args, **_kwargs):
        pytest.fail("invalid request reached record loading")

    monkeypatch.setattr(JsonReviewStore, "locked_load", unexpected_read)
    args = ["export-history", "constructed-record", "--history-position", "1",
            "--expected-state-fingerprint", "a" * 64,
            "--storage-dir", str(tmp_path / "absent")]
    args[args.index(field) + 1] = value
    _assert_refused(args, capsys)
    assert not (tmp_path / "absent").exists()


@pytest.mark.parametrize("missing", ["--history-position", "--expected-state-fingerprint"])
def test_both_explicit_selection_inputs_are_mandatory(tmp_path, capsys, missing):
    args = ["export-history", "constructed-record", "--history-position", "1",
            "--expected-state-fingerprint", "a" * 64]
    index = args.index(missing)
    del args[index:index + 2]
    error = _assert_refused(args, capsys)
    assert missing in error


@pytest.mark.parametrize("command", ["history", "export-history"])
def test_filename_owner_mismatch_is_unavailable(tmp_path, capsys, command):
    state, store, path, fingerprint = _saved(tmp_path)
    imposter_id = "constructed-other-owner"
    imposter = store.directory / f"{imposter_id}.json"
    imposter.write_bytes(path.read_bytes())
    before = imposter.read_bytes(), path.read_bytes()
    if command == "history":
        args = [command, imposter_id, "--storage-dir", str(store.directory)]
    else:
        args = _export_args(state, store, fingerprint)
        args[1] = imposter_id
    _assert_refused(args, capsys)
    assert (imposter.read_bytes(), path.read_bytes()) == before


@pytest.mark.parametrize("format", ["json", "markdown"])
@pytest.mark.parametrize("to_file", [False, True])
def test_missing_historical_provenance_produces_no_report(tmp_path, capsys, format, to_file):
    state = history_only_state()
    state.analysis_history[1].review.criteria_source_provenance = None
    store = JsonReviewStore(tmp_path / "records")
    path = store.save(state)
    fingerprint = store.state_fingerprint(store.load(state.review.review_id))
    before = path.read_bytes()
    target = tmp_path / "report.md" if to_file else None
    _assert_refused(_export_args(state, store, fingerprint, output=target, format=format), capsys)
    assert not (tmp_path / "report.md").exists()
    assert path.read_bytes() == before


@pytest.mark.parametrize("position", ["3", "999999999"])
def test_missing_position_never_falls_back_to_another_analysis(tmp_path, capsys, position):
    state, store, path, fingerprint = _saved(tmp_path)
    before = path.read_bytes()
    target = tmp_path / "report.json"
    _assert_refused(
        _export_args(state, store, fingerprint, output=target, position=position), capsys,
    )
    assert not target.exists()
    assert path.read_bytes() == before


def test_stale_catalog_is_refused_even_if_selected_history_is_unchanged(tmp_path, capsys):
    state, store, path, fingerprint = _saved(tmp_path)
    changed = state.model_copy(deep=True)
    changed.criteria_revision.source_text += " Constructed unrelated saved draft change."
    store.save(changed)
    before = path.read_bytes()
    target = tmp_path / "report.json"
    _assert_refused(_export_args(state, store, fingerprint, output=target), capsys)
    assert not target.exists()
    assert path.read_bytes() == before


@pytest.mark.parametrize("moment", ["before_prepare", "after_prepare"])
def test_saved_change_during_selection_never_exports(tmp_path, capsys, monkeypatch, moment):
    state, store, path, fingerprint = _saved(tmp_path)
    module = _module()
    prepare = module.prepare_historical_analysis
    changed = state.model_copy(deep=True)
    # Removing the earlier retained entry validly retargets one-based position 1.
    changed.analysis_history.pop(0)

    def mutate_during_selection(*args, **kwargs):
        if moment == "before_prepare":
            store.save(changed)
        receipt = prepare(*args, **kwargs)
        if moment == "after_prepare":
            store.save(changed)
        return receipt

    monkeypatch.setattr(module, "prepare_historical_analysis", mutate_during_selection)
    target = tmp_path / "report.json"
    _assert_refused(
        _export_args(state, store, fingerprint, output=target, position="1"), capsys,
    )
    assert not target.exists()
    assert store.load(state.review.review_id).analysis_history[0].review.head_sha == "b" * 40
    assert path.is_file()


def test_existing_output_is_preserved_without_stdout_fallback(tmp_path, capsys):
    state, store, path, fingerprint = _saved(tmp_path)
    before = path.read_bytes()
    target = tmp_path / "report.json"
    target.write_bytes(b"Constructed existing owner output.\n")
    _assert_refused(_export_args(state, store, fingerprint, output=target), capsys)
    assert target.read_bytes() == b"Constructed existing owner output.\n"
    assert path.read_bytes() == before


def test_racing_output_created_after_render_is_preserved(tmp_path, capsys, monkeypatch):
    state, store, path, fingerprint = _saved(tmp_path)
    module = _module()
    render = module.export_historical_json
    target = tmp_path / "report.json"
    before = path.read_bytes()

    def render_then_race(report):
        rendered = render(report)
        target.write_bytes(b"Constructed racing owner output.\n")
        return rendered

    monkeypatch.setattr(module, "export_historical_json", render_then_race)
    _assert_refused(_export_args(state, store, fingerprint, output=target), capsys)
    assert target.read_bytes() == b"Constructed racing owner output.\n"
    assert path.read_bytes() == before


def test_symlink_output_never_changes_its_target(tmp_path, capsys):
    state, store, path, fingerprint = _saved(tmp_path)
    before = path.read_bytes()
    original = tmp_path / "owner-data.json"
    original.write_bytes(b"Constructed owner target.\n")
    target = tmp_path / "report.json"
    try:
        target.symlink_to(original)
    except (NotImplementedError, OSError):
        pytest.skip("creating symlinks is unavailable on this host")
    _assert_refused(_export_args(state, store, fingerprint, output=target), capsys)
    assert target.is_symlink()
    assert original.read_bytes() == b"Constructed owner target.\n"
    assert path.read_bytes() == before


def test_record_mutation_waits_until_file_publication_finishes(tmp_path, monkeypatch):
    """Dropping the consumer lock before publication would allow the writer to finish early."""
    state, store, _, fingerprint = _saved(tmp_path)
    module = _module()
    publish = module.atomic_create_text_with_receipt
    changed = state.model_copy(deep=True)
    changed.criteria_revision.source_text += " Constructed later saved draft."
    attempted, finished = Event(), Event()
    writer = []
    target = tmp_path / "report.json"

    def mutate():
        attempted.set()
        store.save(changed)
        finished.set()

    with ThreadPoolExecutor(max_workers=1) as pool:
        def publish_while_writer_waits(*args, **kwargs):
            writer.append(pool.submit(mutate))
            assert attempted.wait(2)
            assert not finished.wait(0.15), "record changed before historical publication"
            receipt = publish(*args, **kwargs)
            assert target.is_file()
            assert not finished.is_set()
            return receipt

        monkeypatch.setattr(module, "atomic_create_text_with_receipt", publish_while_writer_waits)
        assert main(_export_args(state, store, fingerprint, output=target)) == 0
        writer[0].result(timeout=3)
    assert finished.is_set()
    assert store.load(state.review.review_id).criteria_revision.source_text.endswith(
        "Constructed later saved draft."
    )
