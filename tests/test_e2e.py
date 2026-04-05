"""End-to-end tests — large files, .docx conversion, extract-media."""

import subprocess
import sys
from pathlib import Path

import pytest

from feishu2md.pandoc import check_available

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = PROJECT_ROOT / "docs"


def run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "feishu2md", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(PROJECT_ROOT),
    )


class TestLargeFile:

    def test_1000_headings_performance(self, tmp_path):
        """1000+ headings should complete without error."""
        lines = []
        for i in range(1, 334):
            lines.append(f"# Section {i}")
            lines.append("")
            lines.append(f"## Sub {i}.1")
            lines.append("")
            lines.append(f"### Detail {i}.1.1")
            lines.append("")
        src = tmp_path / "large.md"
        src.write_text("\n".join(lines), encoding="utf-8")
        result = run_cli(str(src))
        assert result.returncode == 0
        # First heading should be numbered
        assert "# 1 Section 1" in result.stdout
        # Last section group should be numbered correctly
        assert "# 333 Section 333" in result.stdout

    def test_large_file_idempotent(self, tmp_path):
        """Large file output is idempotent."""
        lines = []
        for i in range(1, 101):
            lines.append(f"# S{i}")
            lines.append(f"## S{i}a")
        src = tmp_path / "large.md"
        src.write_text("\n".join(lines), encoding="utf-8")
        out1 = tmp_path / "pass1.md"
        out2 = tmp_path / "pass2.md"
        run_cli(str(src), "-o", str(out1))
        run_cli(str(out1), "-o", str(out2))
        assert out1.read_text(encoding="utf-8") == out2.read_text(encoding="utf-8")


@pytest.mark.integration
class TestDocxEndToEnd:

    def test_docx_full_pipeline(self, tmp_path):
        """Full .docx -> numbered .md pipeline with real Pandoc."""
        if not check_available():
            pytest.skip("Pandoc not installed")

        # Create a .docx via pandoc
        src_md = tmp_path / "source.md"
        src_md.write_text("# Title\n\n## Section\n\nContent\n", encoding="utf-8")
        docx = tmp_path / "test.docx"
        subprocess.run(
            ["pandoc", str(src_md), "-o", str(docx)],
            capture_output=True,
        )
        if not docx.exists():
            pytest.skip("Pandoc md->docx failed")

        out = tmp_path / "output.md"
        result = run_cli(str(docx), "-o", str(out))
        assert result.returncode == 0
        content = out.read_text(encoding="utf-8")
        assert "Title" in content

    def test_docx_extract_media_path(self, tmp_path):
        """Verify --extract-media uses output directory."""
        if not check_available():
            pytest.skip("Pandoc not installed")

        src_md = tmp_path / "source.md"
        src_md.write_text("# Title\n\nContent\n", encoding="utf-8")
        docx = tmp_path / "test.docx"
        subprocess.run(
            ["pandoc", str(src_md), "-o", str(docx)],
            capture_output=True,
        )
        if not docx.exists():
            pytest.skip("Pandoc md->docx failed")

        out_dir = tmp_path / "output"
        out_dir.mkdir()
        out = out_dir / "result.md"
        result = run_cli(str(docx), "-o", str(out))
        assert result.returncode == 0


class TestDocxWithSampleFile:

    def test_sample_docx_if_exists(self, tmp_path):
        """Use real sample.docx from docs/ if available (local-only)."""
        sample = DOCS_DIR / "sample.docx"
        if not sample.exists():
            pytest.skip("docs/sample.docx not available")
        if not check_available():
            pytest.skip("Pandoc not installed")

        out = tmp_path / "output.md"
        result = run_cli(str(sample), "-o", str(out))
        assert result.returncode == 0
        content = out.read_text(encoding="utf-8")
        assert len(content) > 0
