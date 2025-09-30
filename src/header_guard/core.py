"""Core utilities for maintaining consistent C++ include guards."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional, Sequence, Tuple


HEADER_SUFFIXES: Tuple[str, ...] = (".h", ".hh", ".hpp", ".hxx", ".h++")
LEADING_COMMENTS = re.compile(
    r"^(?P<prefix>(?:\s*//[^\n]*\n|/\*.*?\*/\s*)*)", re.DOTALL
)
COMMENT_ONLY_PREFIXES: Tuple[str, ...] = ("//", "/*", "*", "*/")
DEFAULT_SPACES_BETWEEN_ENDIF_AND_COMMENT = 2


def is_header(path: Path) -> bool:
    """Return ``True`` when *path* has a recognised header suffix."""

    return path.suffix.lower() in HEADER_SUFFIXES


def find_git_dir(path: Path) -> Optional[Path]:
    """Return the nearest ancestor containing a ``.git`` directory."""

    for candidate in (path,) + tuple(path.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def locate_repo_root(path: Path) -> Path:
    """Locate the repository root starting from *path*.

    Raises
    ------
    ValueError
        If no ``.git`` directory is found in the ancestry.
    """

    root = find_git_dir(path.resolve())
    if root is None:
        raise ValueError("Repository root not found")
    return root


def clean_part(part: str) -> str:
    """Normalise a path component for use in a header guard name."""

    cleaned = "".join((ch if ch.isalnum() else "_") for ch in part.upper())
    return re.sub("_+", "_", cleaned)


def ensure_valid_start(name: str) -> str:
    """Ensure the guard name does not start with a digit."""

    return name if not name[0].isdigit() else f"_{name}"


def header_guard_name(root: Path, path: Path) -> str:
    """Return the canonical include guard name for *path* within *root*."""

    relative = path.resolve().relative_to(root.resolve())
    cleaned = [clean_part(part).strip("_") for part in relative.parts]
    name = "_".join(part for part in cleaned if part) or "HEADER"
    return f"{ensure_valid_start(name)}_"


def comment_prefix(text: str) -> str:
    """Return the leading comment block from *text* if present."""

    match = LEADING_COMMENTS.match(text)
    return "" if match is None else match.group("prefix")


def next_code_index(lines: list[str], start: int) -> Optional[int]:
    """Return the index of the next non-empty line at or after *start*."""

    for index in range(start, len(lines)):
        if lines[index].strip():
            return index
    return None


def is_pragma_once(line: str) -> bool:
    """Return ``True`` when *line* contains ``#pragma once``."""

    return line.lstrip().startswith("#pragma once")


def guard_name_from_ifndef(line: str) -> Optional[str]:
    """Extract the guard name from an ``#ifndef`` line."""

    parts = line.strip().split()
    return parts[1] if len(parts) >= 2 and parts[0] == "#ifndef" else None


def guard_name_from_define(line: str) -> Optional[str]:
    """Extract the guard name from a ``#define`` line."""

    parts = line.strip().split()
    return parts[1] if len(parts) >= 2 and parts[0] == "#define" else None


def macro_guard_define_index(
    lines: list[str], start: int, name: str
) -> Optional[int]:
    """Return the index of the ``#define`` line matching *name*."""

    idx = next_code_index(lines, start + 1)
    return (
        idx
        if idx is not None and guard_name_from_define(lines[idx]) == name
        else None
    )


def matches_endif(line: str, name: str) -> bool:
    """Return ``True`` when *line* closes the guard named *name*."""

    if not line.startswith("#endif"):
        return False
    return line == "#endif" or name in line


def _is_comment_only_line(line: str) -> bool:
    stripped = line.strip()
    return bool(stripped) and any(
        stripped.startswith(prefix) for prefix in COMMENT_ONLY_PREFIXES
    )


def guard_end_index(lines: list[str], name: str) -> Optional[int]:
    """Return the index of the guard-closing ``#endif`` for *name*.

    Trailing file-level comments are ignored so that guards are still detected
    when commentary follows the ``#endif`` line.
    """

    for index in range(len(lines) - 1, -1, -1):
        stripped = lines[index].strip()
        if not stripped:
            continue
        if _is_comment_only_line(stripped):
            continue
        return index if matches_endif(stripped, name) else None
    return None


def remove_guard_segments(
    lines: list[str], start: int, define_index: int, end_index: int
) -> list[str]:
    """Return *lines* with the guard directives removed."""

    return (
        lines[:start]
        + lines[start + 1 : define_index]
        + lines[define_index + 1 : end_index]
        + lines[end_index + 1 :]
    )


def _strip_macro_guard(
    lines: list[str], start: int
) -> tuple[list[str], list[str], bool]:
    name = guard_name_from_ifndef(lines[start])
    if not name:
        return lines, [], False

    define_index = macro_guard_define_index(lines, start, name)
    if define_index is None:
        return lines, [], False

    end_index = guard_end_index(lines, name)
    if end_index is None:
        return lines, [], False

    body = (
        lines[:start]
        + lines[start + 1 : define_index]
        + lines[define_index + 1 : end_index]
    )
    suffix = lines[end_index + 1 :]
    return body, suffix, True


def guard_define_and_end(
    lines: list[str], start: int, name: str
) -> Optional[Tuple[int, int]]:
    """Return the indices of the guard ``#define`` and closing ``#endif``."""

    define_index = macro_guard_define_index(lines, start, name)
    if define_index is None:
        return None

    end_index = guard_end_index(lines, name)
    if end_index is None:
        return None

    return define_index, end_index


def strip_macro_guard(lines: list[str], start: int) -> Tuple[list[str], bool]:
    """Remove a traditional guard starting at *start* if present."""

    body, suffix, removed = _strip_macro_guard(lines, start)
    return body + suffix, removed


def _remove_guard_structure(
    lines: list[str],
) -> tuple[list[str], list[str], bool]:
    start = next_code_index(lines, 0)
    if start is None:
        return lines, [], False

    if is_pragma_once(lines[start]):
        body = lines[:start] + lines[start + 1 :]
        return body, [], True

    body, suffix, removed = _strip_macro_guard(lines, start)
    return body, suffix, removed


def remove_guard_lines(lines: list[str]) -> Tuple[list[str], bool]:
    """Remove any header guard from *lines* and report whether one was found."""

    body, suffix, removed = _remove_guard_structure(lines)
    return body + suffix, removed


def build_guard(
    guard: str,
    body: str,
    spaces_between_endif_and_comment: int = DEFAULT_SPACES_BETWEEN_ENDIF_AND_COMMENT,
) -> str:
    """Return the header content wrapped in a guard named *guard*."""

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
    """Return *text* rewritten to use the guard named *guard*."""

    prefix = comment_prefix(text)
    lines = text[len(prefix) :].splitlines(keepends=True)
    body, suffix, _ = _remove_guard_structure(lines)
    return (
        prefix
        + build_guard(
            guard,
            "".join(body),
            spaces_between_endif_and_comment,
        )
        + "".join(suffix)
    )


def write_if_changed(path: Path, original: str, updated: str) -> None:
    """Write *updated* to *path* when it differs from *original*."""

    if original != updated:
        path.write_text(updated, encoding="utf-8")


def apply_guard(
    path: Path,
    spaces_between_endif_and_comment: int = DEFAULT_SPACES_BETWEEN_ENDIF_AND_COMMENT,
) -> None:
    """Apply the canonical include guard to *path* when it is a header file."""

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
    """Apply guards to all header files contained in *paths*."""

    for path in paths:
        if is_header(path):
            apply_guard(path, spaces_between_endif_and_comment)
