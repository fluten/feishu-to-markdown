"""Tests for CLI argument parsing, validation, and basic I/O (Phase 1)."""

import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "feishu2md.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def run_cli(*args: str, input_text: str | None = None) -> subprocess.CompletedProcess:
    """Helper to run feishu2md.py as a subprocess."""
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        input=input_text,
        encoding="utf-8",
        errors="replace",
    )


# ─── Input Validation ────────────────────────────────────────────────────────


class TestInputValidation:
    """Input file existence and extension checks."""

    def test_file_not_found_exit_code(self):
        result = run_cli("nonexistent.md")
        assert result.returncode == 1

    def test_file_not_found_error_message(self):
        result = run_cli("nonexistent.md")
        assert "Error: file not found: nonexistent.md" in result.stderr

    def test_file_not_found_no_stdout(self):
        result = run_cli("nonexistent.md")
        assert result.stdout == ""

    def test_unsupported_extension_txt(self, tmp_path):
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("hello", encoding="utf-8")
        result = run_cli(str(txt_file))
        assert result.returncode == 1
        assert "Error: unsupported file type '.txt', expected .md or .docx" in result.stderr

    def test_unsupported_extension_html(self, tmp_path):
        html_file = tmp_path / "test.html"
        html_file.write_text("<h1>hi</h1>", encoding="utf-8")
        result = run_cli(str(html_file))
        assert result.returncode == 1
        assert ".html" in result.stderr

    def test_unsupported_extension_no_stdout(self, tmp_path):
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("hello", encoding="utf-8")
        result = run_cli(str(txt_file))
        assert result.stdout == ""

    def test_valid_md_file(self):
        result = run_cli(str(FIXTURES / "basic.md"))
        assert result.returncode == 0

    def test_docx_extension_accepted_but_needs_pandoc(self, tmp_path):
        """docx passes extension check but exits with code 2 (Pandoc not wired yet)."""
        docx_file = tmp_path / "test.docx"
        docx_file.write_bytes(b"PK\x03\x04fake")
        result = run_cli(str(docx_file))
        assert "unsupported file type" not in result.stderr
        assert result.returncode == 2
        assert "pandoc is required" in result.stderr

    def test_no_input_argument(self):
        """Running with no arguments should fail."""
        result = run_cli()
        assert result.returncode != 0


# ─── Mutually Exclusive Args ─────────────────────────────────────────────────


class TestMutuallyExclusiveArgs:
    """--strip-only, --no-strip, --force-strip are mutually exclusive."""

    def test_strip_only_and_no_strip_exit_code(self):
        result = run_cli(str(FIXTURES / "basic.md"), "--strip-only", "--no-strip")
        assert result.returncode == 1

    def test_strip_only_and_no_strip_error_message(self):
        result = run_cli(str(FIXTURES / "basic.md"), "--strip-only", "--no-strip")
        assert (
            "Error: --strip-only, --no-strip, and --force-strip are mutually exclusive"
            in result.stderr
        )

    def test_strip_only_and_force_strip(self):
        result = run_cli(str(FIXTURES / "basic.md"), "--strip-only", "--force-strip")
        assert result.returncode == 1
        assert "mutually exclusive" in result.stderr

    def test_no_strip_and_force_strip(self):
        result = run_cli(str(FIXTURES / "basic.md"), "--no-strip", "--force-strip")
        assert result.returncode == 1
        assert "mutually exclusive" in result.stderr

    def test_all_three(self):
        result = run_cli(
            str(FIXTURES / "basic.md"), "--strip-only", "--no-strip", "--force-strip"
        )
        assert result.returncode == 1

    def test_strip_only_alone_ok(self):
        result = run_cli(str(FIXTURES / "basic.md"), "--strip-only")
        assert result.returncode == 0

    def test_no_strip_alone_ok(self):
        result = run_cli(str(FIXTURES / "basic.md"), "--no-strip")
        assert result.returncode == 0

    def test_force_strip_alone_ok(self):
        result = run_cli(str(FIXTURES / "basic.md"), "--force-strip")
        assert result.returncode == 0

    def test_no_strip_flags_ok(self):
        """No strip flags at all should work fine."""
        result = run_cli(str(FIXTURES / "basic.md"))
        assert result.returncode == 0


# ─── --max-level ──────────────────────────────────────────────────────────────


class TestMaxLevel:
    """--max-level validation."""

    def test_default_is_3(self):
        result = run_cli(str(FIXTURES / "basic.md"))
        assert result.returncode == 0

    def test_valid_values_1_through_6(self):
        for level in range(1, 7):
            result = run_cli(str(FIXTURES / "basic.md"), "--max-level", str(level))
            assert result.returncode == 0, f"--max-level {level} should be valid"

    def test_zero_rejected(self):
        result = run_cli(str(FIXTURES / "basic.md"), "--max-level", "0")
        assert result.returncode != 0

    def test_seven_rejected(self):
        result = run_cli(str(FIXTURES / "basic.md"), "--max-level", "7")
        assert result.returncode != 0

    def test_negative_rejected(self):
        result = run_cli(str(FIXTURES / "basic.md"), "--max-level", "-1")
        assert result.returncode != 0

    def test_non_integer_rejected(self):
        result = run_cli(str(FIXTURES / "basic.md"), "--max-level", "abc")
        assert result.returncode != 0

    def test_float_rejected(self):
        result = run_cli(str(FIXTURES / "basic.md"), "--max-level", "2.5")
        assert result.returncode != 0


# ─── Output Modes ────────────────────────────────────────────────────────────


class TestStdoutOutput:
    """Default output to stdout."""

    def test_basic_content_on_stdout(self):
        result = run_cli(str(FIXTURES / "basic.md"))
        assert result.returncode == 0
        assert "# 产品概述" in result.stdout

    def test_full_content_preserved(self):
        result = run_cli(str(FIXTURES / "basic.md"))
        assert "## 功能设计" in result.stdout
        assert "### 交互逻辑" in result.stdout
        assert "正文内容..." in result.stdout

    def test_no_headings_file(self):
        result = run_cli(str(FIXTURES / "no_headings.md"))
        assert result.returncode == 0
        assert "没有标题的文档" in result.stdout


class TestFileOutput:
    """-o flag writes to a file."""

    def test_output_file_created(self, tmp_path):
        out_file = tmp_path / "output.md"
        result = run_cli(str(FIXTURES / "basic.md"), "-o", str(out_file))
        assert result.returncode == 0
        assert out_file.exists()

    def test_output_file_content(self, tmp_path):
        out_file = tmp_path / "output.md"
        run_cli(str(FIXTURES / "basic.md"), "-o", str(out_file))
        content = out_file.read_text(encoding="utf-8")
        assert "# 产品概述" in content
        assert "## 功能设计" in content

    def test_output_file_lf_newlines(self, tmp_path):
        """Output file must use LF-only newlines."""
        out_file = tmp_path / "output.md"
        run_cli(str(FIXTURES / "basic.md"), "-o", str(out_file))
        raw = out_file.read_bytes()
        assert b"\r\n" not in raw

    def test_stdout_empty_when_using_o(self, tmp_path):
        out_file = tmp_path / "output.md"
        result = run_cli(str(FIXTURES / "basic.md"), "-o", str(out_file))
        assert result.stdout == ""


class TestInplace:
    """--inplace flag with atomic write."""

    def test_inplace_creates_backup(self, tmp_path):
        src = tmp_path / "test.md"
        src.write_text("# Hello\n", encoding="utf-8")
        result = run_cli(str(src), "--inplace")
        assert result.returncode == 0
        assert src.exists()
        bak = tmp_path / "test.md.bak"
        assert bak.exists()

    def test_inplace_backup_has_original_content(self, tmp_path):
        original = "# Hello\n\nWorld\n"
        src = tmp_path / "test.md"
        src.write_text(original, encoding="utf-8")
        run_cli(str(src), "--inplace")
        bak = tmp_path / "test.md.bak"
        assert bak.read_text(encoding="utf-8") == original

    def test_inplace_no_backup(self, tmp_path):
        src = tmp_path / "test.md"
        src.write_text("# Hello\n", encoding="utf-8")
        result = run_cli(str(src), "--inplace", "--no-backup")
        assert result.returncode == 0
        assert src.exists()
        bak = tmp_path / "test.md.bak"
        assert not bak.exists()

    def test_inplace_preserves_content(self, tmp_path):
        original = "# Hello\n\nWorld\n"
        src = tmp_path / "test.md"
        src.write_text(original, encoding="utf-8")
        run_cli(str(src), "--inplace")
        content = src.read_text(encoding="utf-8")
        assert content == original

    def test_inplace_output_lf_newlines(self, tmp_path):
        src = tmp_path / "test.md"
        src.write_text("# Hello\n\nWorld\n", encoding="utf-8")
        run_cli(str(src), "--inplace")
        raw = src.read_bytes()
        assert b"\r\n" not in raw

    def test_inplace_no_tmp_file_left(self, tmp_path):
        """The .tmp file should not remain after completion."""
        src = tmp_path / "test.md"
        src.write_text("# Hello\n", encoding="utf-8")
        run_cli(str(src), "--inplace")
        tmp_file = tmp_path / "test.md.tmp"
        assert not tmp_file.exists()

    def test_inplace_stdout_empty(self, tmp_path):
        src = tmp_path / "test.md"
        src.write_text("# Hello\n", encoding="utf-8")
        result = run_cli(str(src), "--inplace")
        assert result.stdout == ""


# ─── Encoding & Newlines ─────────────────────────────────────────────────────


class TestEncoding:
    """UTF-8 handling and newline normalization."""

    def test_utf8_chinese_content(self):
        result = run_cli(str(FIXTURES / "basic.md"))
        assert result.returncode == 0
        assert "产品概述" in result.stdout
        assert "功能设计" in result.stdout
        assert "交互逻辑" in result.stdout

    def test_crlf_normalized_to_lf(self, tmp_path):
        src = tmp_path / "crlf.md"
        src.write_bytes(b"# Hello\r\n\r\nWorld\r\n")
        result = run_cli(str(src))
        assert result.returncode == 0
        assert "\r\n" not in result.stdout
        assert "# Hello" in result.stdout
        assert "World" in result.stdout

    def test_crlf_output_file_lf(self, tmp_path):
        """CRLF input → LF-only output file."""
        src = tmp_path / "crlf.md"
        src.write_bytes(b"# Hello\r\n\r\nWorld\r\n")
        out = tmp_path / "out.md"
        run_cli(str(src), "-o", str(out))
        raw = out.read_bytes()
        assert b"\r\n" not in raw
        assert b"# Hello\n" in raw

    def test_empty_file(self):
        result = run_cli(str(FIXTURES / "empty.md"))
        assert result.returncode == 0
        assert result.stdout == ""

    def test_empty_file_output(self, tmp_path):
        out = tmp_path / "out.md"
        result = run_cli(str(FIXTURES / "empty.md"), "-o", str(out))
        assert result.returncode == 0
        assert out.read_text(encoding="utf-8") == ""


# ─── Help & Usage ────────────────────────────────────────────────────────────


class TestHelpAndUsage:
    """--help flag and parameter descriptions."""

    def test_help_exit_code(self):
        result = run_cli("--help")
        assert result.returncode == 0

    def test_help_shows_program_name(self):
        result = run_cli("--help")
        assert "feishu2md" in result.stdout

    def test_help_shows_all_options(self):
        result = run_cli("--help")
        for opt in ["--max-level", "--strip-only", "--no-strip",
                     "--force-strip", "--inplace", "--no-backup", "-o"]:
            assert opt in result.stdout, f"{opt} missing from --help output"
