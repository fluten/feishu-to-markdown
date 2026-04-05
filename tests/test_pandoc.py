"""Tests for pandoc.py — version detection, parameter selection, error handling."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from feishu2md.models import PandocNotFoundError, PandocVersionError
from feishu2md.pandoc import check_available, convert, get_version


def _mock_version_output(version_str: str) -> MagicMock:
    """Create a mock subprocess result with pandoc version output."""
    mock = MagicMock()
    mock.stdout = f"pandoc {version_str}\nCompiled with pandoc-types"
    mock.returncode = 0
    return mock


# --- check_available ---


class TestCheckAvailable:

    @patch("feishu2md.pandoc.subprocess.run")
    def test_returns_true_when_installed(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        assert check_available() is True

    @patch("feishu2md.pandoc.subprocess.run", side_effect=FileNotFoundError)
    def test_returns_false_when_not_installed(self, mock_run):
        assert check_available() is False


# --- get_version ---


class TestGetVersion:

    @patch("feishu2md.pandoc.subprocess.run")
    def test_parses_3x_version(self, mock_run):
        mock_run.return_value = _mock_version_output("3.1.2")
        assert get_version() == (3, 1, 2)

    @patch("feishu2md.pandoc.subprocess.run")
    def test_parses_2x_version(self, mock_run):
        mock_run.return_value = _mock_version_output("2.19.1")
        assert get_version() == (2, 19, 1)

    @patch("feishu2md.pandoc.subprocess.run")
    def test_parses_major_only(self, mock_run):
        mock_run.return_value = _mock_version_output("3")
        assert get_version() == (3,)

    @patch("feishu2md.pandoc.subprocess.run", side_effect=FileNotFoundError)
    def test_raises_not_found(self, mock_run):
        with pytest.raises(PandocNotFoundError, match="pandoc is required"):
            get_version()

    @patch("feishu2md.pandoc.subprocess.run")
    def test_raises_not_found_on_bad_output(self, mock_run):
        mock = MagicMock()
        mock.stdout = "some random output"
        mock_run.return_value = mock
        with pytest.raises(PandocNotFoundError):
            get_version()


# --- convert: version check ---


class TestConvertVersionCheck:

    @patch("feishu2md.pandoc.subprocess.run")
    def test_version_1x_raises(self, mock_run):
        mock_run.return_value = _mock_version_output("1.19.2")
        with pytest.raises(PandocVersionError, match="pandoc >= 2.0 required"):
            convert(Path("test.docx"))

    @patch("feishu2md.pandoc.subprocess.run")
    def test_version_1x_includes_found_version(self, mock_run):
        mock_run.return_value = _mock_version_output("1.19.2")
        with pytest.raises(PandocVersionError, match="1.19.2"):
            convert(Path("test.docx"))


# --- convert: parameter selection ---


class TestConvertParameters:

    @patch("feishu2md.pandoc.subprocess.run")
    def test_uses_gfm_format(self, mock_run):
        """GFM output for best table rendering (pipe tables + HTML fallback)."""
        mock_run.side_effect = [
            _mock_version_output("3.1.2"),
            MagicMock(returncode=0),
        ]

        with patch("feishu2md.pandoc.Path.read_text", return_value="# Title"):
            with patch("feishu2md.pandoc.Path.unlink"):
                convert(Path("test.docx"))

        conversion_call = mock_run.call_args_list[1]
        cmd = conversion_call[0][0]
        # Should use -t gfm
        assert "-t" in cmd
        gfm_idx = cmd.index("-t")
        assert cmd[gfm_idx + 1] == "gfm"

    @patch("feishu2md.pandoc.subprocess.run")
    def test_2x_also_uses_gfm(self, mock_run):
        """Pandoc 2.x also uses GFM format."""
        mock_run.side_effect = [
            _mock_version_output("2.19.1"),
            MagicMock(returncode=0),
        ]

        with patch("feishu2md.pandoc.Path.read_text", return_value="# Title"):
            with patch("feishu2md.pandoc.Path.unlink"):
                convert(Path("test.docx"))

        conversion_call = mock_run.call_args_list[1]
        cmd = conversion_call[0][0]
        assert "-t" in cmd
        gfm_idx = cmd.index("-t")
        assert cmd[gfm_idx + 1] == "gfm"

    @patch("feishu2md.pandoc.subprocess.run")
    def test_wrap_none_always_present(self, mock_run):
        mock_run.side_effect = [
            _mock_version_output("3.1.2"),
            MagicMock(returncode=0),
        ]

        with patch("feishu2md.pandoc.Path.read_text", return_value="# Title"):
            with patch("feishu2md.pandoc.Path.unlink"):
                convert(Path("test.docx"))

        conversion_call = mock_run.call_args_list[1]
        cmd = conversion_call[0][0]
        assert "--wrap=none" in cmd

    @patch("feishu2md.pandoc.subprocess.run")
    def test_extract_media_with_output_dir(self, mock_run):
        mock_run.side_effect = [
            _mock_version_output("3.1.2"),
            MagicMock(returncode=0),
        ]

        with patch("feishu2md.pandoc.Path.read_text", return_value="# Title"):
            with patch("feishu2md.pandoc.Path.unlink"):
                convert(Path("test.docx"), output_dir=Path("/out"))

        conversion_call = mock_run.call_args_list[1]
        cmd = conversion_call[0][0]
        media_args = [a for a in cmd if "--extract-media" in a]
        assert len(media_args) == 1

    @patch("feishu2md.pandoc.subprocess.run")
    def test_extract_media_without_output_dir(self, mock_run):
        mock_run.side_effect = [
            _mock_version_output("3.1.2"),
            MagicMock(returncode=0),
        ]

        docx = Path("/docs/test.docx")
        with patch("feishu2md.pandoc.Path.read_text", return_value="# Title"):
            with patch("feishu2md.pandoc.Path.unlink"):
                convert(docx, output_dir=None)

        conversion_call = mock_run.call_args_list[1]
        cmd = conversion_call[0][0]
        media_args = [a for a in cmd if "--extract-media" in a]
        assert len(media_args) == 1
        # Should use docx parent dir (resolved absolute path)
        assert str(docx.parent.resolve()) in media_args[0]


# --- integration test (requires real Pandoc) ---


class TestConvertIntegration:

    @pytest.mark.integration
    def test_docx_end_to_end(self, tmp_path):
        """End-to-end .docx conversion with real Pandoc.
        Skip if Pandoc is not installed."""
        if not check_available():
            pytest.skip("Pandoc not installed")

        # Create a minimal .docx via pandoc (md -> docx -> md roundtrip)
        src_md = tmp_path / "source.md"
        src_md.write_text("# Title\n\nContent\n", encoding="utf-8")
        docx_file = tmp_path / "test.docx"

        # Convert md to docx first
        import subprocess, sys
        result = subprocess.run(
            ["pandoc", str(src_md), "-o", str(docx_file)],
            capture_output=True,
        )
        if result.returncode != 0:
            pytest.skip("Pandoc md->docx conversion failed")

        # Now test our convert function
        md_text = convert(docx_file, output_dir=tmp_path)
        assert isinstance(md_text, str)
        assert len(md_text) > 0
        assert "Title" in md_text
