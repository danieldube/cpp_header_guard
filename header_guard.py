from __future__ import annotations
from pathlib import Path
import argparse
import re
from typing import Optional, Tuple

HEADER_EXTS: set[str] = {".h", ".hpp", ".hh", ".hxx", ".inl", ".tpp"}
LEAD_RE = re.compile(r'^(?:\s*//[^\n]*\n|/\*.*?\*/\s*|\s*\n)+', re.DOTALL)
PRAGMA_RE = re.compile(r'^\s*#\s*pragma\s+once\s*(?:\r?\n)?', re.IGNORECASE)
GUARD_START_RE = re.compile(
    r'^\s*#\s*ifndef\s+([A-Za-z_][A-Za-z0-9_]*)\s*$.*?^\s*#\s*define\s+\1\s*$',
    re.MULTILINE | re.DOTALL,
)
END_RE = re.compile(r'^\s*#\s*endif\b.*(?:\r?\n)?', re.MULTILINE)


def is_header_file(p: Path) -> bool:
    return p.suffix.lower() in HEADER_EXTS


def find_repo_root(start: Path) -> Path:
    for d in [start] + list(start.parents):
        if (d / ".git").exists():
            return d
    return Path(start.anchor or "/")


def rel_to_root(root: Path, file: Path) -> Path:
    try:
        return file.resolve().relative_to(root.resolve())
    except Exception:
        return file.resolve().relative_to(file.anchor)


def macro_from_rel_path(rel: Path) -> str:
    s = str(rel).replace("\\", "/").upper()
    s = re.sub(r"[^A-Z0-9]+", "_", s).strip("_") + "_"
    return re.sub(r"_+", "_", s)


def leading_comments_span(s: str) -> int:
    m = LEAD_RE.match(s)
    return m.end() if m else 0


def strip_pragma_once(s: str, i: int) -> Tuple[str, bool]:
    m = PRAGMA_RE.match(s[i:])
    return (s[:i] + s[i + m.end():], True) if m else (s, False)


def find_guard(s: str) -> Optional[Tuple[int, int, int, int, str]]:
    m = GUARD_START_RE.search(s)
    if not m:
        return None
    e = list(END_RE.finditer(s, m.end()))
    return (m.start(), m.end(), e[-1].start(), e[-1].end(), m.group(1)) if e else None


def guard_block(m: str) -> str:
    return f"#ifndef {m}\n#define {m}\n"


def end_block(m: str) -> str:
    return f"#endif  // {m}\n"


def insert_guard(s: str, i: int, m: str) -> str:
    body = s[i:] if s.endswith("\n") else s[i:] + "\n"
    return s[:i] + guard_block(m) + body + end_block(m)


def rebuild_guard(s: str, span: Tuple[int, int, int, int, str], m: str) -> str:
    a, bs, be, be2, _ = span
    body = s[bs:be]
    if body.startswith("\n"): body = body[1:]
    if not body.endswith("\n"): body += "\n"
    return s[:a] + guard_block(m) + body + end_block(m) + s[be2:]


def process_header_text(s: str, rel_path: str) -> str:
    macro = macro_from_rel_path(Path(rel_path))
    i = leading_comments_span(s)
    s, _ = strip_pragma_once(s, i)
    g = find_guard(s)
    return rebuild_guard(s, g, macro) if g else insert_guard(s, i, macro)


def _cli_args() -> tuple[Path, Optional[Path]]:
    ap = argparse.ArgumentParser(description="Normalize C/C++ header guards.")
    ap.add_argument("path"); ap.add_argument("--root")
    a = ap.parse_args()
    return Path(a.path), (Path(a.root) if a.root else None)


def run(path: Path, root: Optional[Path]) -> None:
    if not is_header_file(path): return
    text = path.read_text(encoding="utf-8")
    rel = rel_to_root(root or find_repo_root(path), path)
    new = process_header_text(text, str(rel))
    if new != text: path.write_text(new, encoding="utf-8")


def main() -> int:
    p, r = _cli_args(); run(p, r); return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
