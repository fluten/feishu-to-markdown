"""Tests for writer.py — stdout, file, inplace output."""

from pathlib import Path
from unittest.mock import patch

import pytest

from feishu2md.models import LineInfo, WriteError
from feishu2md.writer import write


def _make_lines(*texts: str) -> list[LineInfo]:
    return [LineInfo(line_number=i + 1, raw_text=t) for i, t in enumerate(texts)]


# --- stdout output ---


class TestStdoutOutput:

    def test_stdout_basic(self, capsys):
        lines = _make_lines("# Title", "", "Content")
        write(lines, output=None, inplace=False, backup=True)
        captured = capsys.readouterr()
        assert "# Title" in captured.out
        assert "Content" in captured.out

    def test_stdout_lines_joined_with_newline(self, capsys):
        lines = _make_lines("line1", "line2", "line3")
        write(lines, output=None, inplace=False, backup=True)
        captured = capsys.readouterr()
        assert captured.out == "line1\nline2\nline3"

    def test_stdout_empty_lines(self, capsys):
        lines = _make_lines("")
        write(lines, output=None, inplace=False, backup=True)
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_stdout_chinese_content(self, capsys):
        lines = _make_lines("# Title", "Content")
        write(lines, output=None, inplace=False, backup=True)
        captured = capsys.readouterr()
        assert "Title" in captured.out

    def test_stdout_no_trailing_newline_added(self, capsys):
        """Writer joins with \\n but does not add extra trailing newline."""
        lines = _make_lines("a", "b")
        write(lines, output=None, inplace=False, backup=True)
        captured = capsys.readouterr()
        assert captured.out == "a\nb"
        assert not captured.out.endswith("\n\n")


# --- file output ---


class TestFileOutput:

    def test_file_created(self, tmp_path):
        out = tmp_path / "output.md"
        lines = _make_lines("# Title", "", "Content")
        write(lines, output=out, inplace=False, backup=True)
        assert out.exists()

    def test_file_content_correct(self, tmp_path):
        out = tmp_path / "output.md"
        lines = _make_lines("# Title", "", "Content")
        write(lines, output=out, inplace=False, backup=True)
        content = out.read_text(encoding="utf-8")
        assert content == "# Title\n\nContent"

    def test_file_encoding_utf8(self, tmp_path):
        out = tmp_path / "output.md"
        lines = _make_lines("# Title")
        write(lines, output=out, inplace=False, backup=True)
        raw = out.read_bytes()
        # UTF-8 BOM should NOT be present
        assert not raw.startswith(b"\xef\xbb\xbf")

    def test_file_newlines_lf_only(self, tmp_path):
        out = tmp_path / "output.md"
        lines = _make_lines("line1", "line2", "line3")
        write(lines, output=out, inplace=False, backup=True)
        raw = out.read_bytes()
        assert b"\r\n" not in raw
        assert b"\n" in raw

    def test_file_lines_joined(self, tmp_path):
        out = tmp_path / "output.md"
        lines = _make_lines("a", "b", "c")
        write(lines, output=out, inplace=False, backup=True)
        content = out.read_text(encoding="utf-8")
        assert content == "a\nb\nc"

    def test_file_empty_content(self, tmp_path):
        out = tmp_path / "output.md"
        lines = _make_lines("")
        write(lines, output=out, inplace=False, backup=True)
        content = out.read_text(encoding="utf-8")
        assert content == ""

    def test_file_overwrites_existing(self, tmp_path):
        out = tmp_path / "output.md"
        out.write_text("old content", encoding="utf-8")
        lines = _make_lines("new content")
        write(lines, output=out, inplace=False, backup=True)
        content = out.read_text(encoding="utf-8")
        assert content == "new content"

    def test_stdout_not_used_when_output_set(self, tmp_path, capsys):
        out = tmp_path / "output.md"
        lines = _make_lines("content")
        write(lines, output=out, inplace=False, backup=True)
        captured = capsys.readouterr()
        assert captured.out == ""


# --- inplace with backup ---


class TestInplaceWithBackup:

    def test_file_updated(self, tmp_path):
        src = tmp_path / "test.md"
        src.write_text("old", encoding="utf-8")
        lines = _make_lines("new")
        write(lines, output=None, inplace=True, backup=True, input_path=src)
        assert src.read_text(encoding="utf-8") == "new"

    def test_bak_created(self, tmp_path):
        src = tmp_path / "test.md"
        src.write_text("old", encoding="utf-8")
        lines = _make_lines("new")
        write(lines, output=None, inplace=True, backup=True, input_path=src)
        bak = tmp_path / "test.md.bak"
        assert bak.exists()

    def test_bak_has_original_content(self, tmp_path):
        src = tmp_path / "test.md"
        src.write_text("original content", encoding="utf-8")
        lines = _make_lines("new content")
        write(lines, output=None, inplace=True, backup=True, input_path=src)
        bak = tmp_path / "test.md.bak"
        assert bak.read_text(encoding="utf-8") == "original content"

    def test_tmp_file_cleaned_up(self, tmp_path):
        src = tmp_path / "test.md"
        src.write_text("old", encoding="utf-8")
        lines = _make_lines("new")
        write(lines, output=None, inplace=True, backup=True, input_path=src)
        tmp = tmp_path / "test.md.tmp"
        assert not tmp.exists()

    def test_output_lf_newlines(self, tmp_path):
        src = tmp_path / "test.md"
        src.write_text("old", encoding="utf-8")
        lines = _make_lines("line1", "line2")
        write(lines, output=None, inplace=True, backup=True, input_path=src)
        raw = src.read_bytes()
        assert b"\r\n" not in raw


# --- inplace without backup ---


class TestInplaceNoBackup:

    def test_no_bak_file(self, tmp_path):
        src = tmp_path / "test.md"
        src.write_text("old", encoding="utf-8")
        lines = _make_lines("new")
        write(lines, output=None, inplace=True, backup=False, input_path=src)
        bak = tmp_path / "test.md.bak"
        assert not bak.exists()

    def test_file_updated(self, tmp_path):
        src = tmp_path / "test.md"
        src.write_text("old", encoding="utf-8")
        lines = _make_lines("new")
        write(lines, output=None, inplace=True, backup=False, input_path=src)
        assert src.read_text(encoding="utf-8") == "new"


# --- parameter validation ---


class TestParameterValidation:

    def test_inplace_without_input_path_raises(self):
        lines = _make_lines("content")
        with pytest.raises(WriteError, match="inplace=True requires input_path"):
            write(lines, output=None, inplace=True, backup=True, input_path=None)


# --- atomic write safety ---


class TestAtomicWriteSafety:

    def test_rename_failure_preserves_original(self, tmp_path):
        """If renaming .tmp to original fails, .bak is restored."""
        src = tmp_path / "test.md"
        src.write_text("original", encoding="utf-8")
        lines = _make_lines("new")

        # Mock the second rename (tmp -> input_path) to fail
        real_rename = Path.rename

        call_count = 0

        def mock_rename(self, target):
            nonlocal call_count
            call_count += 1
            if call_count == 2:  # second rename: tmp -> input_path
                raise OSError("mock rename failure")
            return real_rename(self, target)

        with patch.object(Path, "rename", mock_rename):
            with pytest.raises(WriteError):
                write(lines, output=None, inplace=True, backup=True, input_path=src)

        # Original file should be restored
        assert src.exists()
        assert src.read_text(encoding="utf-8") == "original"
