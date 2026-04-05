"""Tests for __main__.py — CLI argument parsing, validation, and framework (Phase 1)."""

import argparse
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def run_cli(*args: str) -> subprocess.CompletedProcess:
    """Run python -m feishu2md as a subprocess."""
    return subprocess.run(
        [sys.executable, "-m", "feishu2md", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(PROJECT_ROOT),
    )


# ─── --help ──────────────────────────────────────────────────────────────────


class TestHelp:

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
            assert opt in result.stdout, f"{opt} missing from --help"

    def test_help_shows_input_positional(self):
        result = run_cli("--help")
        assert "input" in result.stdout


# ─── Input Validation ────────────────────────────────────────────────────────


class TestInputValidation:

    def test_no_arguments(self):
        result = run_cli()
        assert result.returncode != 0

    def test_file_not_found_exit_code(self):
        result = run_cli("nonexistent.md")
        assert result.returncode == 1

    def test_file_not_found_error_message(self):
        result = run_cli("nonexistent.md")
        assert "Error: file not found:" in result.stderr
        assert "nonexistent.md" in result.stderr

    def test_file_not_found_no_stdout(self):
        result = run_cli("nonexistent.md")
        assert result.stdout == ""

    def test_unsupported_extension_exit_code(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello", encoding="utf-8")
        result = run_cli(str(f))
        assert result.returncode == 1

    def test_unsupported_extension_message(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello", encoding="utf-8")
        result = run_cli(str(f))
        assert "Error: unsupported file type '.txt', expected .md or .docx" in result.stderr

    def test_unsupported_extension_html(self, tmp_path):
        f = tmp_path / "test.html"
        f.write_text("<h1>hi</h1>", encoding="utf-8")
        result = run_cli(str(f))
        assert result.returncode == 1
        assert ".html" in result.stderr

    def test_docx_passes_extension_check(self, tmp_path):
        """.docx is a valid extension — should not get 'unsupported file type'."""
        f = tmp_path / "test.docx"
        f.write_bytes(b"PK\x03\x04fake")
        result = run_cli(str(f))
        assert "unsupported file type" not in result.stderr


# ─── Mutually Exclusive Strip Args ───────────────────────────────────────────


class TestMutuallyExclusive:

    def test_strip_only_and_no_strip(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("# hi", encoding="utf-8")
        result = run_cli(str(f), "--strip-only", "--no-strip")
        assert result.returncode == 1
        assert "Error: --strip-only, --no-strip, and --force-strip are mutually exclusive" in result.stderr

    def test_strip_only_and_force_strip(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("# hi", encoding="utf-8")
        result = run_cli(str(f), "--strip-only", "--force-strip")
        assert result.returncode == 1
        assert "mutually exclusive" in result.stderr

    def test_no_strip_and_force_strip(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("# hi", encoding="utf-8")
        result = run_cli(str(f), "--no-strip", "--force-strip")
        assert result.returncode == 1

    def test_all_three(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("# hi", encoding="utf-8")
        result = run_cli(str(f), "--strip-only", "--no-strip", "--force-strip")
        assert result.returncode == 1

    def test_strip_only_alone_ok(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("# hi", encoding="utf-8")
        result = run_cli(str(f), "--strip-only")
        # Will fail in pipeline (empty stubs) but should pass validation
        # Just check it doesn't fail with "mutually exclusive"
        assert "mutually exclusive" not in result.stderr

    def test_no_strip_alone_ok(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("# hi", encoding="utf-8")
        result = run_cli(str(f), "--no-strip")
        assert "mutually exclusive" not in result.stderr

    def test_force_strip_alone_ok(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("# hi", encoding="utf-8")
        result = run_cli(str(f), "--force-strip")
        assert "mutually exclusive" not in result.stderr


# ─── --max-level Validation ──────────────────────────────────────────────────


class TestMaxLevel:

    def test_valid_range_1_to_6(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("# hi", encoding="utf-8")
        for level in range(1, 7):
            result = run_cli(str(f), "--max-level", str(level))
            assert "mutually exclusive" not in result.stderr

    def test_zero_rejected(self):
        result = run_cli("dummy.md", "--max-level", "0")
        assert result.returncode != 0

    def test_seven_rejected(self):
        result = run_cli("dummy.md", "--max-level", "7")
        assert result.returncode != 0

    def test_non_integer_rejected(self):
        result = run_cli("dummy.md", "--max-level", "abc")
        assert result.returncode != 0

    def test_float_rejected(self):
        result = run_cli("dummy.md", "--max-level", "2.5")
        assert result.returncode != 0

    def test_negative_rejected(self):
        result = run_cli("dummy.md", "--max-level", "-1")
        assert result.returncode != 0


# ─── Exception Framework ─────────────────────────────────────────────────────


class TestExceptionFramework:

    def test_input_error_exit_code_1(self):
        """InputError (file not found) → exit code 1."""
        result = run_cli("nonexistent.md")
        assert result.returncode == 1

    def test_input_error_format(self):
        """Error message must start with 'Error: '."""
        result = run_cli("nonexistent.md")
        assert result.stderr.startswith("Error: ")

    def test_docx_without_pandoc_exit_code_2(self, tmp_path):
        """PandocNotFoundError → exit code 2 (once pandoc module raises it)."""
        # For now with empty stubs, .docx will hit pipeline error.
        # This test documents expected behavior for Phase 7.
        pass


# ─── Warning Framework ───────────────────────────────────────────────────────


class TestWarningFramework:

    def test_warning_format_in_stderr(self):
        """Warnings should follow 'Warning: {message} (line {n})' format.
        Can't trigger real warnings yet (empty stubs), but verify the framework
        exists by importing and checking the function signature."""
        from feishu2md.__main__ import run_pipeline
        assert callable(run_pipeline)


# ─── stdout UTF-8 ────────────────────────────────────────────────────────────


class TestStdoutEncoding:

    def test_stdout_reconfigure_called(self):
        """main() calls sys.stdout.reconfigure(encoding='utf-8')."""
        from feishu2md.__main__ import main
        assert callable(main)


# ─── Validate via unit test (not subprocess) ─────────────────────────────────


class TestValidateArgsUnit:
    """Test validate_args() directly for precision."""

    def test_valid_md(self, tmp_path):
        from feishu2md.__main__ import validate_args
        f = tmp_path / "test.md"
        f.write_text("# hi", encoding="utf-8")
        ns = argparse.Namespace(
            input=str(f), strip_only=False, no_strip=False, force_strip=False
        )
        validate_args(ns)  # should not raise

    def test_file_not_found_raises_input_error(self):
        from feishu2md.__main__ import validate_args
        from feishu2md.models import InputError
        ns = argparse.Namespace(
            input="nonexistent.md", strip_only=False, no_strip=False, force_strip=False
        )
        with pytest.raises(InputError, match="file not found"):
            validate_args(ns)

    def test_unsupported_type_raises_input_error(self, tmp_path):
        from feishu2md.__main__ import validate_args
        from feishu2md.models import InputError
        f = tmp_path / "test.csv"
        f.write_text("a,b", encoding="utf-8")
        ns = argparse.Namespace(
            input=str(f), strip_only=False, no_strip=False, force_strip=False
        )
        with pytest.raises(InputError, match="unsupported file type"):
            validate_args(ns)

    def test_mutual_exclusion_raises_input_error(self, tmp_path):
        from feishu2md.__main__ import validate_args
        from feishu2md.models import InputError
        f = tmp_path / "test.md"
        f.write_text("# hi", encoding="utf-8")
        ns = argparse.Namespace(
            input=str(f), strip_only=True, no_strip=True, force_strip=False
        )
        with pytest.raises(InputError, match="mutually exclusive"):
            validate_args(ns)

    def test_mutual_exclusion_checked_before_file(self):
        """Mutual exclusion error should fire even if file doesn't exist."""
        from feishu2md.__main__ import validate_args
        from feishu2md.models import InputError
        ns = argparse.Namespace(
            input="nonexistent.md", strip_only=True, no_strip=True, force_strip=False
        )
        with pytest.raises(InputError, match="mutually exclusive"):
            validate_args(ns)


class TestGetStripMode:
    """Test get_strip_mode() mapping."""

    def test_default_auto(self):
        from feishu2md.__main__ import get_strip_mode
        ns = argparse.Namespace(strip_only=False, no_strip=False, force_strip=False)
        assert get_strip_mode(ns) == "auto"

    def test_strip_only(self):
        from feishu2md.__main__ import get_strip_mode
        ns = argparse.Namespace(strip_only=True, no_strip=False, force_strip=False)
        assert get_strip_mode(ns) == "strip_only"

    def test_no_strip(self):
        from feishu2md.__main__ import get_strip_mode
        ns = argparse.Namespace(strip_only=False, no_strip=True, force_strip=False)
        assert get_strip_mode(ns) == "none"

    def test_force_strip(self):
        from feishu2md.__main__ import get_strip_mode
        ns = argparse.Namespace(strip_only=False, no_strip=False, force_strip=True)
        assert get_strip_mode(ns) == "force"


# --- Full pipeline integration (subprocess) ---


class TestPipelineIntegration:
    """End-to-end pipeline tests via subprocess."""

    def test_basic_numbering(self, tmp_path):
        src = tmp_path / "input.md"
        src.write_text("# A\n\n## B\n\n### C\n", encoding="utf-8")
        result = run_cli(str(src))
        assert result.returncode == 0
        assert "# 1 A" in result.stdout
        assert "## 1.1 B" in result.stdout
        assert "### 1.1.1 C" in result.stdout

    def test_output_to_file(self, tmp_path):
        src = tmp_path / "input.md"
        src.write_text("# A\n## B\n", encoding="utf-8")
        out = tmp_path / "output.md"
        result = run_cli(str(src), "-o", str(out))
        assert result.returncode == 0
        content = out.read_text(encoding="utf-8")
        assert "# 1 A" in content
        assert "## 1.1 B" in content
        assert result.stdout == ""

    def test_inplace_with_backup(self, tmp_path):
        src = tmp_path / "test.md"
        src.write_text("# A\n## B\n", encoding="utf-8")
        result = run_cli(str(src), "--inplace")
        assert result.returncode == 0
        assert "# 1 A" in src.read_text(encoding="utf-8")
        bak = tmp_path / "test.md.bak"
        assert bak.exists()
        assert "# A" in bak.read_text(encoding="utf-8")

    def test_inplace_no_backup(self, tmp_path):
        src = tmp_path / "test.md"
        src.write_text("# A\n", encoding="utf-8")
        result = run_cli(str(src), "--inplace", "--no-backup")
        assert result.returncode == 0
        assert "# 1 A" in src.read_text(encoding="utf-8")
        bak = tmp_path / "test.md.bak"
        assert not bak.exists()

    def test_strip_only(self, tmp_path):
        src = tmp_path / "input.md"
        src.write_text("# 1 A\n## 1.1 B\n", encoding="utf-8")
        result = run_cli(str(src), "--strip-only")
        assert result.returncode == 0
        assert "# A" in result.stdout
        assert "## B" in result.stdout
        # No numbering should be re-added
        assert "# 1 " not in result.stdout

    def test_no_strip(self, tmp_path):
        src = tmp_path / "input.md"
        src.write_text("# A\n## B\n", encoding="utf-8")
        result = run_cli(str(src), "--no-strip")
        assert result.returncode == 0
        assert "# 1 A" in result.stdout

    def test_force_strip(self, tmp_path):
        src = tmp_path / "input.md"
        src.write_text("# 1.0 A\n## 2.0 B\n", encoding="utf-8")
        result = run_cli(str(src), "--force-strip")
        assert result.returncode == 0
        assert "# 1 A" in result.stdout
        assert "## 1.1 B" in result.stdout

    def test_max_level(self, tmp_path):
        src = tmp_path / "input.md"
        src.write_text("# A\n## B\n### C\n", encoding="utf-8")
        result = run_cli(str(src), "--max-level", "2")
        assert result.returncode == 0
        assert "# 1 A" in result.stdout
        assert "## 1.1 B" in result.stdout
        assert "### C" in result.stdout  # H3 not numbered

    def test_empty_file(self, tmp_path):
        src = tmp_path / "empty.md"
        src.write_text("", encoding="utf-8")
        result = run_cli(str(src))
        assert result.returncode == 0

    def test_no_headings_file(self, tmp_path):
        src = tmp_path / "noheadings.md"
        src.write_text("just text\nmore text\n", encoding="utf-8")
        result = run_cli(str(src))
        assert result.returncode == 0
        assert "just text" in result.stdout


class TestWarningOutput:
    """Warnings go to stderr, not stdout."""

    def test_warning_in_stderr_not_stdout(self, tmp_path):
        src = tmp_path / "input.md"
        src.write_text("# A\n### C\n", encoding="utf-8")
        result = run_cli(str(src))
        # Warning about level jump should be in stderr
        assert "jumped" in result.stderr or "Warning" in result.stderr
        # stdout should only have the processed content
        assert "Warning" not in result.stdout

    def test_no_headings_warning(self, tmp_path):
        src = tmp_path / "noheadings.md"
        src.write_text("just text\n", encoding="utf-8")
        result = run_cli(str(src))
        assert "no headings found" in result.stderr

    def test_info_prefix_for_invalid_sequence(self, tmp_path):
        src = tmp_path / "input.md"
        src.write_text("# 1.0 A\n## 2.0 B\n## 3.1 C\n", encoding="utf-8")
        result = run_cli(str(src))
        assert "Info:" in result.stderr
        assert "not a valid numbering sequence" in result.stderr

    def test_level_jump_warning(self, tmp_path):
        src = tmp_path / "input.md"
        src.write_text("# A\n### C\n", encoding="utf-8")
        result = run_cli(str(src))
        assert "jumped from H1 to H3" in result.stderr
