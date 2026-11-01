"""Independent safety checks for CONSTRUCTED saved-requirements CLI handoff."""

import builtins
import json
from concurrent.futures import ThreadPoolExecutor
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
    return state, store, path, store.state_fingerprint(store.load(state.review.review_id))


def _args(state, store, fingerprint, *, output=None, format="json", position="2"):
    args = [
        "export-criteria-changes", state.review.review_id,
        "--history-position", position, "--expected-state-fingerprint", fingerprint,
        "--storage-dir", str(store.directory), "--format", format,
    ]
    if output is not None:
        args.extend(["--output", str(output)])
    return args


def _refused(args, capsys):
    with pytest.raises(SystemExit) as error:
        main(args)
    assert error.value.code == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "invalid choice: 'export-criteria-changes'" not in captured.err
    assert "Traceback" not in captured.err
    return captured.err


@pytest.mark.parametrize("field,value", [
    ("--history-position", "0"), ("--history-position", "-1"),
    ("--history-position", "1.0"), ("--history-position", "true"),
    ("--expected-state-fingerprint", "A" * 64),
    ("--expected-state-fingerprint", "g" * 64),
    ("--expected-state-fingerprint", "a" * 63),
    ("--expected-state-fingerprint", "a" * 65),
])
def test_invalid_request_is_rejected_before_any_record_read(
    tmp_path, capsys, monkeypatch, field, value,
):
    def unexpected_read(*_args, **_kwargs):
        pytest.fail("invalid request reached saved-record loading")

    monkeypatch.setattr(JsonReviewStore, "locked_load", unexpected_read)
    args = ["export-criteria-changes", "constructed-record", "--history-position", "1",
            "--expected-state-fingerprint", "a" * 64,
            "--storage-dir", str(tmp_path / "absent")]
    args[args.index(field) + 1] = value
    _refused(args, capsys)
    assert not (tmp_path / "absent").exists()


@pytest.mark.parametrize("missing", ["--history-position", "--expected-state-fingerprint"])
def test_selection_fields_are_mandatory_before_record_reads(tmp_path, capsys, monkeypatch, missing):
    def unexpected_read(*_args, **_kwargs):
        pytest.fail("incomplete request reached saved-record loading")

    monkeypatch.setattr(JsonReviewStore, "locked_load", unexpected_read)
    args = ["export-criteria-changes", "constructed-record", "--history-position", "1",
            "--expected-state-fingerprint", "a" * 64,
            "--storage-dir", str(tmp_path / "absent")]
    index = args.index(missing)
    del args[index:index + 2]
    assert missing in _refused(args, capsys)
    assert not (tmp_path / "absent").exists()


def test_filename_owner_mismatch_produces_no_report(tmp_path, capsys):
    state, store, path, fingerprint = _saved(tmp_path)
    imposter = store.directory / "constructed-imposter.json"
    imposter.write_bytes(path.read_bytes())
    before = path.read_bytes(), imposter.read_bytes()
    args = _args(state, store, fingerprint, output=tmp_path / "report.json")
    args[1] = "constructed-imposter"
    _refused(args, capsys)
    assert not (tmp_path / "report.json").exists()
    assert (path.read_bytes(), imposter.read_bytes()) == before


def test_current_only_saved_change_invalidates_catalog_selection(tmp_path, capsys):
    state, store, path, fingerprint = _saved(tmp_path)
    changed = state.model_copy(deep=True)
    changed.criteria_revision.source_text += " CONSTRUCTED later draft."
    store.save(changed)
    before = path.read_bytes()
    target = tmp_path / "report.json"
    _refused(_args(state, store, fingerprint, output=target), capsys)
    assert not target.exists()
    assert path.read_bytes() == before


@pytest.mark.parametrize("moment", ["before_prepare", "after_prepare"])
@pytest.mark.parametrize("change", ["current_criteria", "history_retarget"])
def test_saved_changes_during_selection_never_publish(
    tmp_path, capsys, monkeypatch, moment, change,
):
    state, store, _, fingerprint = _saved(tmp_path)
    module = _module()
    prepare = module.prepare_criteria_comparison
    changed = state.model_copy(deep=True)
    if change == "current_criteria":
        changed.criteria_revision.criteria[0].text += " CONSTRUCTED revised text."
    else:
        changed.analysis_history.pop(0)

    def mutate_during_selection(*args, **kwargs):
        if moment == "before_prepare":
            store.save(changed)
        receipt = prepare(*args, **kwargs)
        if moment == "after_prepare":
            store.save(changed)
        return receipt

    monkeypatch.setattr(module, "prepare_criteria_comparison", mutate_during_selection)
    target = tmp_path / "report.json"
    _refused(_args(state, store, fingerprint, output=target, position="1"), capsys)
    assert not target.exists()
    assert store.load(state.review.review_id) == changed


@pytest.mark.parametrize("format", ["json", "markdown"])
def test_unknown_provenance_is_visible_without_relaxing_acceptance_export(
    tmp_path, capsys, format,
):
    state, store, path, _ = _saved(tmp_path)
    state.analysis_history[1].review.criteria_source_provenance = None
    store.save(state)
    fingerprint = store.state_fingerprint(store.load(state.review.review_id))
    before = path.read_bytes()
    assert main(_args(state, store, fingerprint, format=format)) == 0
    output = capsys.readouterr().out
    if format == "json":
        report = json.loads(output)
        assert report["previous"]["source_provenance"] is None
        assert report["current"]["confirmed"] is False
    else:
        assert "Not recorded; provenance remains unknown." in output
    history_args = _args(state, store, fingerprint, format=format,
                         output=tmp_path / "historical.txt")
    history_args[0] = "export-history"
    _refused(history_args, capsys)
    assert not (tmp_path / "historical.txt").exists()
    assert path.read_bytes() == before


@pytest.mark.parametrize("format", ["json", "markdown"])
@pytest.mark.parametrize("to_file", [False, True])
def test_render_failure_publishes_neither_partial_stdout_nor_file(
    tmp_path, capsys, monkeypatch, format, to_file,
):
    state, store, path, fingerprint = _saved(tmp_path)
    module = _module()
    renderer_name = f"export_criteria_comparison_{format}"
    render = getattr(module, renderer_name)
    before = path.read_bytes()
    target = tmp_path / "report.txt"

    def fail_after_full_render(report):
        assert render(report)
        raise ValueError("CONSTRUCTED rendering refusal before publication")

    monkeypatch.setattr(module, renderer_name, fail_after_full_render)
    _refused(_args(state, store, fingerprint, format=format,
                  output=target if to_file else None), capsys)
    assert not target.exists()
    assert path.read_bytes() == before


def test_existing_output_is_preserved_without_stdout_fallback(tmp_path, capsys):
    state, store, path, fingerprint = _saved(tmp_path)
    before = path.read_bytes()
    target = tmp_path / "report.json"
    target.write_bytes(b"CONSTRUCTED existing owner output.\n")
    _refused(_args(state, store, fingerprint, output=target), capsys)
    assert target.read_bytes() == b"CONSTRUCTED existing owner output.\n"
    assert path.read_bytes() == before


def test_racing_output_created_after_render_is_preserved(tmp_path, capsys, monkeypatch):
    state, store, path, fingerprint = _saved(tmp_path)
    module = _module()
    render = module.export_criteria_comparison_json
    target = tmp_path / "report.json"
    before = path.read_bytes()

    def render_then_race(report):
        rendered = render(report)
        target.write_bytes(b"CONSTRUCTED racing owner output.\n")
        return rendered

    monkeypatch.setattr(module, "export_criteria_comparison_json", render_then_race)
    _refused(_args(state, store, fingerprint, output=target), capsys)
    assert target.read_bytes() == b"CONSTRUCTED racing owner output.\n"
    assert path.read_bytes() == before


@pytest.mark.parametrize("existing_target", [False, True])
def test_symlink_output_never_creates_or_changes_its_target(tmp_path, capsys, existing_target):
    state, store, path, fingerprint = _saved(tmp_path)
    before = path.read_bytes()
    original = tmp_path / "owner-data.json"
    if existing_target:
        original.write_bytes(b"CONSTRUCTED owner target.\n")
    target = tmp_path / "report.json"
    try:
        target.symlink_to(original)
    except (NotImplementedError, OSError):
        pytest.skip("creating symlinks is unavailable on this host")
    _refused(_args(state, store, fingerprint, output=target), capsys)
    assert target.is_symlink()
    if existing_target:
        assert original.read_bytes() == b"CONSTRUCTED owner target.\n"
    else:
        assert not original.exists()
    assert path.read_bytes() == before


@pytest.mark.parametrize("to_file", [False, True])
def test_record_lock_is_held_through_stdout_or_file_publication(
    tmp_path, capsys, monkeypatch, to_file,
):
    state, store, _, fingerprint = _saved(tmp_path)
    module = _module()
    publish = module.atomic_create_text_with_receipt if to_file else builtins.print
    changed = state.model_copy(deep=True)
    changed.criteria_revision.source_text += " CONSTRUCTED subsequent draft."
    attempted, finished = Event(), Event()
    target = tmp_path / "report.json"
    writer = []

    def mutate():
        attempted.set()
        store.save(changed)
        finished.set()

    with ThreadPoolExecutor(max_workers=1) as pool:
        def publish_with_competing_writer(*args, **kwargs):
            writer.append(pool.submit(mutate))
            assert attempted.wait(2)
            assert not finished.wait(0.15), "saved record changed before report publication"
            receipt = publish(*args, **kwargs)
            assert not finished.is_set(), "record lock ended during publication"
            return receipt

        monkeypatch.setattr(module, "atomic_create_text_with_receipt" if to_file else "print",
                            publish_with_competing_writer, raising=to_file)
        assert main(_args(state, store, fingerprint, output=target if to_file else None)) == 0
        writer[0].result(timeout=3)
    assert finished.is_set()
    assert store.load(state.review.review_id) == changed
    if to_file:
        assert target.is_file() and capsys.readouterr().out == ""
    else:
        assert json.loads(capsys.readouterr().out)["current"]["source_text"] != (
            changed.criteria_revision.source_text
        )
