"""Ensure C++ headers use consistent include guards."""

from __future__ import annotations

from dataclasses import dataclass
import re
from pathlib import Path
from typing import Optional, Sequence, Tuple

import click

HEADER_SUFFIXES: Tuple[str, ...] = (".h", ".hh", ".hpp", ".hxx", ".h++")
LEADING_COMMENTS = re.compile(
    r"^(?P<prefix>(?:\s*//[^\n]*\n|/\*.*?\*/\s*)*)", re.DOTALL
)
DEFAULT_SPACES_BETWEEN_ENDIF_AND_COMMENT = 2


@dataclass(frozen=True)
class Arguments:
    """Command line arguments supported by the header guard tool."""

    paths: Tuple[Path, ...]
    spaces_between_endif_and_comment: int


def is_header(path: Path) -> bool:
    return path.suffix.lower() in HEADER_SUFFIXES


def find_git_dir(path: Path) -> Optional[Path]:
    for candidate in (path,) + tuple(path.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def locate_repo_root(path: Path) -> Path:
    root = find_git_dir(path.resolve())
    if root is None:
        raise ValueError("Repository root not found")
    return root


def clean_part(part: str) -> str:
    cleaned = "".join((ch if ch.isalnum() else "_") for ch in part.upper())
    return re.sub("_+", "_", cleaned)


def ensure_valid_start(name: str) -> str:
    return name if not name[0].isdigit() else f"_{name}"


def header_guard_name(root: Path, path: Path) -> str:
    relative = path.resolve().relative_to(root.resolve())
    cleaned = [clean_part(part).strip("_") for part in relative.parts]
    name = "_".join(part for part in cleaned if part) or "HEADER"
    return f"{ensure_valid_start(name)}_"


def comment_prefix(text: str) -> str:
    match = LEADING_COMMENTS.match(text)
    return "" if match is None else match.group("prefix")


def next_code_index(lines: list[str], start: int) -> Optional[int]:
    for index in range(start, len(lines)):
        if lines[index].strip():
            return index
    return None


def is_pragma_once(line: str) -> bool:
    return line.lstrip().startswith("#pragma once")


def guard_name_from_ifndef(line: str) -> Optional[str]:
    parts = line.strip().split()
    return parts[1] if len(parts) >= 2 and parts[0] == "#ifndef" else None


def guard_name_from_define(line: str) -> Optional[str]:
    parts = line.strip().split()
    return parts[1] if len(parts) >= 2 and parts[0] == "#define" else None


def macro_guard_define_index(
    lines: list[str], start: int, name: str
) -> Optional[int]:
    idx = next_code_index(lines, start + 1)
    return (
        idx
        if idx is not None and guard_name_from_define(lines[idx]) == name
        else None
    )


def matches_endif(line: str, name: str) -> bool:
    if not line.startswith("#endif"):
        return False
    return line == "#endif" or name in line


def guard_end_index(lines: list[str], name: str) -> Optional[int]:
    indices = [idx for idx, line in enumerate(lines) if line.strip()]
    if not indices:
        return None
    return (
        indices[-1]
        if matches_endif(lines[indices[-1]].strip(), name)
        else None
    )


def guard_define_and_end(
    lines: list[str], start: int, name: str
) -> Optional[Tuple[int, int]]:
    define_index = macro_guard_define_index(lines, start, name)
    if define_index is None:
        return None
    return (
        (define_index, end_index)
        if (end_index := guard_end_index(lines, name)) is not None
        else None
    )


def remove_guard_segments(
    lines: list[str], start: int, define_index: int, end_index: int
) -> list[str]:
    return (
        lines[:start]
        + lines[start + 1 : define_index]
        + lines[define_index + 1 : end_index]
        + lines[end_index + 1 :]
    )


def strip_macro_guard(lines: list[str], start: int) -> Tuple[list[str], bool]:
    name = guard_name_from_ifndef(lines[start])
    info = guard_define_and_end(lines, start, name) if name else None
    return (
        (lines, False)
        if info is None
        else (
            remove_guard_segments(lines, start, info[0], info[1]),
            True,
        )
    )


def remove_guard_lines(lines: list[str]) -> Tuple[list[str], bool]:
    start = next_code_index(lines, 0)
    if start is None:
        return lines, False
    return (
        (
            lines[:start] + lines[start + 1 :],
            True,
        )
        if is_pragma_once(lines[start])
        else strip_macro_guard(lines, start)
    )


def build_guard(
    guard: str,
    body: str,
    spaces_between_endif_and_comment: int = DEFAULT_SPACES_BETWEEN_ENDIF_AND_COMMENT,
) -> str:
    content = body.lstrip("\n")
    content = (
        f"{content}\n" if content and not content.endswith("\n") else content
    )
    spacing = " " * spaces_between_endif_and_comment
    return (
        f"#ifndef {guard}\n"
        f"#define {guard}\n\n"
        f"{content}#endif{spacing}// {guard}\n"
    )


def ensure_guard(
    text: str,
    guard: str,
    spaces_between_endif_and_comment: int = DEFAULT_SPACES_BETWEEN_ENDIF_AND_COMMENT,
) -> str:
    prefix = comment_prefix(text)
    body_lines, _ = remove_guard_lines(
        text[len(prefix) :].splitlines(keepends=True)
    )
    return prefix + build_guard(
        guard,
        "".join(body_lines),
        spaces_between_endif_and_comment,
    )


def write_if_changed(path: Path, original: str, updated: str) -> None:
    if original != updated:
        path.write_text(updated, encoding="utf-8")


def apply_guard(
    path: Path,
    spaces_between_endif_and_comment: int = DEFAULT_SPACES_BETWEEN_ENDIF_AND_COMMENT,
) -> None:
    root = locate_repo_root(path)
    text = path.read_text(encoding="utf-8")
    guard = header_guard_name(root, path)
    write_if_changed(
        path,
        text,
        ensure_guard(text, guard, spaces_between_endif_and_comment),
    )


def process_paths(
    paths: Sequence[Path], spaces_between_endif_and_comment: int
) -> None:
    for path in paths:
        if is_header(path):
            apply_guard(path, spaces_between_endif_and_comment)


@click.command()
@click.argument("paths", nargs=-1, type=click.Path(path_type=Path))
@click.option(
    "--spaces-between-endif-and-comment",
    "spaces_between_endif_and_comment",
    type=click.IntRange(min=0),
    default=DEFAULT_SPACES_BETWEEN_ENDIF_AND_COMMENT,
    show_default=True,
    help="Number of spaces between '#endif' and the trailing comment.",
)
def cli(
    paths: Tuple[Path, ...], spaces_between_endif_and_comment: int
) -> None:
    if not paths:
        raise click.UsageError("Provide at least one header path to format.")
    process_paths(paths, spaces_between_endif_and_comment)


CLI = cli


def parse_args(argv: Sequence[str]) -> Arguments:
    if not argv:
        raise ValueError("Usage: header-guard <path> [<path> ...]")

    arguments = list(argv[1:])
    try:
        with CLI.make_context("header-guard", arguments) as context:
            paths = tuple(context.params["paths"])
            spaces_between_endif_and_comment = context.params[
                "spaces_between_endif_and_comment"
            ]
    except click.ClickException as error:
        raise ValueError(str(error)) from error

    if not paths:
        raise ValueError("Usage: header-guard <path> [<path> ...]")

    return Arguments(paths, spaces_between_endif_and_comment)


def main(argv: Optional[Sequence[str]] = None) -> None:
    if argv is None:
        CLI.main()
        return

    arguments = parse_args(argv)
    process_paths(arguments.paths, arguments.spaces_between_endif_and_comment)


if __name__ == "__main__":
    main()
