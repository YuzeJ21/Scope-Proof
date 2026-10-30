"""Git source coordinates use LF, not Python's broader text-separator set."""

import importlib

import pytest


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("", []),
        ("one", ["one"]),
        ("one\n", ["one"]),
        ("\n", [""]),
        ("one\n\nlast", ["one", "", "last"]),
        ("one\n\n", ["one", ""]),
        ("one\r\ntwo\r\n", ["one", "two"]),
        ("one\r\nlast\r", ["one", "last\r"]),
        ("one\r\r\nlast", ["one\r", "last"]),
    ],
)
def test_lf_crlf_blank_and_eof_coordinates(source, expected):
    splitter = importlib.import_module("scopeproof_core.source_lines").split_git_source_lines
    assert splitter(source) == expected


@pytest.mark.parametrize(
    "separator", ["\r", "\v", "\f", "\x1c", "\x1d", "\x1e", "\x85", "\u2028", "\u2029"]
)
def test_non_lf_separators_remain_inside_their_source_record(separator):
    splitter = importlib.import_module("scopeproof_core.source_lines").split_git_source_lines
    assert splitter(f"before{separator}after\ntarget_identifier()\n") == [
        f"before{separator}after",
        "target_identifier()",
    ]


def test_patch_mode_keeps_cr_for_protocol_aware_eof_handling():
    splitter = importlib.import_module("scopeproof_core.source_lines").split_git_source_lines
    assert splitter("+line\r\n\\ No newline at end of file\n", strip_crlf=False) == [
        "+line\r", "\\ No newline at end of file",
    ]
    assert splitter("last\r", strip_crlf=False) == ["last\r"]
