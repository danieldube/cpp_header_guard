"""Tests for header_guard script."""

from __future__ import annotations

from pathlib import Path

import pytest

import header_guard


def test_parse_args_returns_path() -> None:
    arguments = header_guard.parse_args(["script", "file.hpp"])
    assert arguments.paths == (Path("file.hpp"),)
    assert (
        arguments.spaces_between_endif_and_comment
        == header_guard.DEFAULT_SPACES_BETWEEN_ENDIF_AND_COMMENT
    )


def test_parse_args_raises_on_missing_argument() -> None:
    with pytest.raises(ValueError):
        header_guard.parse_args(["script"])


def test_parse_args_supports_multiple_paths() -> None:
    arguments = header_guard.parse_args(["script", "first.h", "second.hpp"])
    assert arguments.paths == (Path("first.h"), Path("second.hpp"))


def test_parse_args_accepts_spacing_option() -> None:
    arguments = header_guard.parse_args(
        ["script", "--spaces-between-endif-and-comment", "4", "file.hpp"]
    )
    assert arguments.paths == (Path("file.hpp"),)
    assert arguments.spaces_between_endif_and_comment == 4


def test_parse_args_rejects_negative_spacing() -> None:
    with pytest.raises(ValueError):
        header_guard.parse_args(
            ["script", "--spaces-between-endif-and-comment", "-1", "file.hpp"]
        )


@pytest.mark.parametrize(
    "filename, expected",
    [
        ("file.h", True),
        ("file.hpp", True),
        ("file.txt", False),
        ("file.H", True),
    ],
)
def test_is_header(filename: str, expected: bool) -> None:
    assert header_guard.is_header(Path(filename)) is expected


def test_find_git_dir_locates_root(tmp_path: Path) -> None:
    git_root = tmp_path / "project"
    git_root.mkdir()
    (git_root / ".git").mkdir()
    nested = git_root / "src"
    nested.mkdir()
    assert header_guard.find_git_dir(nested) == git_root


def test_locate_repo_root_raises_when_missing(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        header_guard.locate_repo_root(tmp_path)


def test_clean_part_replaces_invalid_characters() -> None:
    assert header_guard.clean_part("dir-name") == "DIR_NAME"


def test_ensure_valid_start_prefixes_digit() -> None:
    assert header_guard.ensure_valid_start("1FOO") == "_1FOO"


def test_header_guard_name_builds_expected_name(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    file_path = tmp_path / "include" / "foo" / "bar-baz.hpp"
    file_path.parent.mkdir(parents=True)
    expected = "INCLUDE_FOO_BAR_BAZ_HPP_"
    assert header_guard.header_guard_name(tmp_path, file_path) == expected


def test_comment_prefix_handles_block_and_line_comments() -> None:
    content = "// line\n/* block */\nint value;\n"
    prefix = header_guard.comment_prefix(content)
    assert prefix == "// line\n/* block */\n"


def test_comment_prefix_handles_multiline_block_comment() -> None:
    content = "/* first line\n * second line\n */\nint value;\n"
    prefix = header_guard.comment_prefix(content)
    assert prefix == "/* first line\n * second line\n */\n"


def test_next_code_index_finds_first_non_empty_line() -> None:
    lines = ["\n", "", " code\n"]
    assert header_guard.next_code_index(lines, 0) == 2


def test_is_pragma_once_detects_statement() -> None:
    assert header_guard.is_pragma_once("  #pragma once\n")


def test_guard_name_parsing_functions() -> None:
    ifndef = "#ifndef GUARD_NAME\n"
    define = "#define GUARD_NAME\n"
    assert header_guard.guard_name_from_ifndef(ifndef) == "GUARD_NAME"
    assert header_guard.guard_name_from_define(define) == "GUARD_NAME"


def test_macro_guard_define_index_returns_expected_index() -> None:
    lines = ["\n", "#ifndef GUARD\n", "#define GUARD\n", "content\n"]
    assert header_guard.macro_guard_define_index(lines, 1, "GUARD") == 2


def test_guard_end_index_identifies_last_guard_line() -> None:
    lines = [
        "#ifndef GUARD\n",
        "#define GUARD\n",
        "content\n",
        "#endif  // GUARD\n",
    ]
    assert header_guard.guard_end_index(lines, "GUARD") == 3


def test_matches_endif_checks_guard_name() -> None:
    assert header_guard.matches_endif("#endif  // GUARD", "GUARD")
    assert not header_guard.matches_endif("#endif  // OTHER", "GUARD")


def test_guard_define_and_end_returns_indices() -> None:
    lines = ["#ifndef GUARD\n", "#define GUARD\n", "content\n", "#endif\n"]
    assert header_guard.guard_define_and_end(lines, 0, "GUARD") == (1, 3)


def test_remove_guard_segments_returns_body() -> None:
    lines = [
        "#ifndef GUARD\n",
        "#define GUARD\n",
        "\n",
        "content\n",
        "#endif\n",
    ]
    expected = ["\n", "content\n"]
    assert header_guard.remove_guard_segments(lines, 0, 1, 4) == expected


def test_strip_macro_guard_removes_guard_lines() -> None:
    lines = [
        "#ifndef GUARD\n",
        "#define GUARD\n",
        "int value;\n",
        "#endif\n",
    ]
    stripped, removed = header_guard.strip_macro_guard(lines, 0)
    assert removed is True
    assert stripped == ["int value;\n"]


def test_remove_guard_lines_handles_pragma_once() -> None:
    lines = ["#pragma once\n", "int value;\n"]
    stripped, removed = header_guard.remove_guard_lines(lines)
    assert removed is True
    assert stripped == ["int value;\n"]


def test_remove_guard_lines_without_guard_returns_original() -> None:
    lines = ["int value;\n"]
    stripped, removed = header_guard.remove_guard_lines(lines)
    assert removed is False
    assert stripped == lines


def test_build_guard_wraps_body() -> None:
    body = "int value;\n"
    expected = (
        "#ifndef GUARD\n"
        "#define GUARD\n\n"
        "int value;\n"
        "#endif  // GUARD\n"
    )
    assert header_guard.build_guard("GUARD", body) == expected


def test_build_guard_honours_spacing_option() -> None:
    body = "int value;\n"
    result = header_guard.build_guard("GUARD", body, spaces_between_endif_and_comment=0)
    assert result.endswith("#endif// GUARD\n")


def test_ensure_guard_inserts_guard_after_comments() -> None:
    text = "// header\nint value;\n"
    updated = header_guard.ensure_guard(text, "GUARD")
    assert updated == (
        "// header\n"
        "#ifndef GUARD\n"
        "#define GUARD\n\n"
        "int value;\n"
        "#endif  // GUARD\n"
    )


def test_ensure_guard_replaces_existing_guard() -> None:
    text = (
        "#ifndef OLD_GUARD\n"
        "#define OLD_GUARD\n\n"
        "int value;\n"
        "#endif  // OLD_GUARD\n"
    )
    updated = header_guard.ensure_guard(text, "NEW_GUARD")
    assert updated == (
        "#ifndef NEW_GUARD\n"
        "#define NEW_GUARD\n\n"
        "int value;\n"
        "#endif  // NEW_GUARD\n"
    )


def test_ensure_guard_can_customize_spacing() -> None:
    text = "int value;\n"
    updated = header_guard.ensure_guard(
        text,
        "GUARD",
        spaces_between_endif_and_comment=3,
    )
    assert updated.endswith("#endif   // GUARD\n")


def test_write_if_changed_writes_when_needed(tmp_path: Path) -> None:
    path = tmp_path / "file.h"
    path.write_text("old", encoding="utf-8")
    header_guard.write_if_changed(path, "old", "new")
    assert path.read_text(encoding="utf-8") == "new"


def test_main_processes_multiple_paths(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()

    header_one = tmp_path / "first.hpp"
    header_one.write_text("int value;\n", encoding="utf-8")

    header_two = tmp_path / "include" / "second.h"
    header_two.parent.mkdir()
    header_two.write_text("int other;\n", encoding="utf-8")

    non_header = tmp_path / "note.txt"
    non_header.write_text("plain text\n", encoding="utf-8")

    header_guard.main(
        [
            "script",
            str(header_one),
            str(header_two),
            str(non_header),
        ]
    )

    guard_one = header_guard.header_guard_name(tmp_path, header_one)
    guard_two = header_guard.header_guard_name(tmp_path, header_two)

    assert header_one.read_text(encoding="utf-8") == header_guard.ensure_guard(
        "int value;\n", guard_one
    )
    assert header_two.read_text(encoding="utf-8") == header_guard.ensure_guard(
        "int other;\n", guard_two
    )
    assert non_header.read_text(encoding="utf-8") == "plain text\n"


def test_write_if_changed_skips_when_unchanged(tmp_path: Path) -> None:
    path = tmp_path / "file.h"
    path.write_text("same", encoding="utf-8")
    header_guard.write_if_changed(path, "same", "same")
    assert path.read_text(encoding="utf-8") == "same"


def test_apply_guard_updates_file(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    header = tmp_path / "include" / "sample.h"
    header.parent.mkdir(parents=True)
    header.write_text("int value;\n", encoding="utf-8")
    header_guard.apply_guard(header)
    expected = (
        "#ifndef INCLUDE_SAMPLE_H_\n#define INCLUDE_SAMPLE_H_\n\nint value;\n"
        "#endif  // INCLUDE_SAMPLE_H_\n"
    )
    assert header.read_text(encoding="utf-8") == expected


def test_apply_guard_accepts_spacing_parameter(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    header = tmp_path / "include" / "sample.h"
    header.parent.mkdir(parents=True)
    header.write_text("int value;\n", encoding="utf-8")
    header_guard.apply_guard(header, spaces_between_endif_and_comment=1)
    assert header.read_text(encoding="utf-8").endswith("#endif // INCLUDE_SAMPLE_H_\n")


def test_main_processes_header_file(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    header = tmp_path / "src" / "value.hpp"
    header.parent.mkdir(parents=True)
    header.write_text("int value;\n", encoding="utf-8")
    header_guard.main(["script", str(header)])
    expected = (
        "#ifndef SRC_VALUE_HPP_\n#define SRC_VALUE_HPP_\n\nint value;\n"
        "#endif  // SRC_VALUE_HPP_\n"
    )
    assert header.read_text(encoding="utf-8") == expected


def test_main_respects_spacing_option(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    header = tmp_path / "src" / "value.hpp"
    header.parent.mkdir(parents=True)
    header.write_text("int value;\n", encoding="utf-8")
    header_guard.main(
        [
            "script",
            "--spaces-between-endif-and-comment",
            "5",
            str(header),
        ]
    )
    assert header.read_text(encoding="utf-8").endswith("#endif     // SRC_VALUE_HPP_\n")


def test_main_ignores_non_header(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    source = tmp_path / "src" / "main.cpp"
    source.parent.mkdir(parents=True)
    source.write_text("int main() { return 0; }\n", encoding="utf-8")
    header_guard.main(["script", str(source)])
    assert source.read_text(encoding="utf-8") == "int main() { return 0; }\n"
