"""Tests for writer.py — stdout output and file output."""

from pathlib import Path

from feishu2md.models import LineInfo
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
