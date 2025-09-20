import textwrap
from pathlib import Path
import pytest
import header_guard as hg


# ---------- Unit tests ----------

def test_is_header_file():
    assert hg.is_header_file(Path("a.hpp"))
    assert not hg.is_header_file(Path("a.cpp"))


def test_macro_from_rel_path_basic():
    assert hg.macro_from_rel_path(Path("src/lib/vec3.hpp")) == "SRC_LIB_VEC3_HPP_"


def test_macro_from_rel_path_normalizes():
    p = Path(r"include\\foo+bar/baz qux.hh")
    assert hg.macro_from_rel_path(p) == "INCLUDE_FOO_BAR_BAZ_QUX_HH_"


def test_leading_comments_span_block():
    s = """/* license */\n\nint x;\n"""
    assert hg.leading_comments_span(s) > 0


def test_leading_comments_span_line_comments():
    s = "// a\n// b\nint x;\n"
    assert hg.leading_comments_span(s) == len("// a\n// b\n")


def test_strip_pragma_once_at_top():
    head = "/* h */\n"; body = "#pragma once\nint x;\n"
    s = head + body
    out, removed = hg.strip_pragma_once(s, len(head))
    assert removed and "#pragma once" not in out


def test_strip_pragma_once_not_at_lead():
    s = "int x;\n#pragma once\n"
    out, removed = hg.strip_pragma_once(s, 0)
    assert not removed and out == s


def test_find_guard_none():
    assert hg.find_guard("int x;\n") is None


def test_find_guard_detects_and_spans():
    s = textwrap.dedent(
        """
        // c
        #ifndef OLD_GUARD_
        #define OLD_GUARD_
        int x;
        #endif // OLD_GUARD_
        """
    )
    g = hg.find_guard(s)
    assert g and g[0] < g[1] < g[2] < g[3] and g[4] == "OLD_GUARD_"


def test_guard_block_and_end_block():
    m = "MACRO_"
    assert hg.guard_block(m) == "#ifndef MACRO_\n#define MACRO_\n"
    assert hg.end_block(m) == "#endif  // MACRO_\n"


def test_insert_guard_shapes_body():
    body = "int x;\n"
    out = hg.insert_guard(body, 0, "M_")
    assert out.startswith("#ifndef M_\n#define M_\n")
    assert out.rstrip().endswith("#endif  // M_")


def test_rebuild_guard_preserves_body():
    s = textwrap.dedent(
        """
        #ifndef A_
        #define A_
        int x;\n
        #endif // A_
        tail
        """
    )
    g = hg.find_guard(s)
    out = hg.rebuild_guard(s, g, "B_")
    assert "#ifndef B_" in out and "A_" not in out
    assert "int x;\n#endif  // B_" in out and "tail" in out


# ---------- Component tests (string-based) ----------

@pytest.mark.parametrize(
    "rel, src, exp_macro",
    [
        (
            "include/foo/bar.h",
            "/* hdr */\nint x;\n",
            "INCLUDE_FOO_BAR_H_",
        ),
        (
            "src/x.hpp",
            "// hdr\n#pragma once\nint x;\n",
            "SRC_X_HPP_",
        ),
        (
            "a/b/c.hh",
            textwrap.dedent(
                """
                // top
                #ifndef WRONG_
                #define WRONG_
                int x;
                #endif
                """
            ),
            "A_B_C_HH_",
        ),
    ],
)
def test_process_header_text_end_to_end(rel, src, exp_macro):
    out = hg.process_header_text(src, rel)
    assert f"#ifndef {exp_macro}\n#define {exp_macro}\n" in out
    assert out.rstrip().endswith(f"#endif  // {exp_macro}")


def test_idempotent_canonical():
    macro = "SRC_LIB_V_H_"
    s = f"#ifndef {macro}\n#define {macro}\nint x;\n#endif  // {macro}\n"
    out = hg.process_header_text(s, "src/lib/v.h")
    assert out == s


def test_mixed_line_endings_windows():
    s = "#pragma once\r\nint x;\r\n"
    out = hg.process_header_text(s, "w.h")
    assert out.count("#pragma once") == 0 and "#ifndef W_H_" in out


def test_no_comments_inserts_at_top():
    out = hg.process_header_text("int x;\n", "a.h")
    assert out.startswith("#ifndef A_H_\n#define A_H_\n")


def test_process_header_text_single_line_comments():
    s = "// a\n// b\nint x;\n"
    out = hg.process_header_text(s, "c.h")
    assert out.startswith("// a\n// b\n#ifndef C_H_\n#define C_H_\n")


def test_process_header_text_mixed_separators():
    rel = r"dir\\sub-dir/file name.tpp"
    out = hg.process_header_text("int x;\n", rel)
    assert "#ifndef DIR_SUB_DIR_FILE_NAME_TPP_" in out


def test_process_header_text_windows_newline_body_preserved():
    s = "#ifndef OLD\n#define OLD\r\nbody\r\n#endif\r\n"
    out = hg.process_header_text(s, "x.h")
    assert out.count("#ifndef X_H_") == 1


def test_no_comments_trailing_newline():
    out = hg.process_header_text("int x;", "b.h")
    assert out.endswith("#endif  // B_H_\n")


# Optional small I/O smoke test using tmp_path

def test_run_smoke(tmp_path):
    p = tmp_path / "inc" / "v.hpp"; p.parent.mkdir()
    p.write_text("#pragma once\nint x;\n", encoding="utf-8")
    hg.run(p, root=tmp_path)
    t = p.read_text(encoding="utf-8")
    assert "#pragma once" not in t and "#ifndef INC_V_HPP_" in t
