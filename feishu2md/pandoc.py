"""Pandoc 调用模块。封装所有 Pandoc 相关操作。"""

import re
import subprocess
import tempfile
from pathlib import Path

from feishu2md.models import PandocNotFoundError, PandocVersionError

_VERSION_RE = re.compile(r"pandoc(?:\.exe)?\s+(\d+(?:\.\d+)*)")


def check_available() -> bool:
    """Check if pandoc is installed and accessible."""
    try:
        subprocess.run(
            ["pandoc", "--version"],
            capture_output=True,
            check=False,
        )
        return True
    except FileNotFoundError:
        return False


def get_version() -> tuple[int, ...]:
    """Get pandoc version as a tuple of ints, e.g. (3, 1, 2).

    Raises PandocNotFoundError if pandoc is not installed.
    """
    try:
        result = subprocess.run(
            ["pandoc", "--version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        raise PandocNotFoundError(
            "pandoc is required for .docx input. "
            "Install: https://pandoc.org/installing.html"
        )

    m = _VERSION_RE.search(result.stdout)
    if not m:
        raise PandocNotFoundError(
            "pandoc is required for .docx input. "
            "Install: https://pandoc.org/installing.html"
        )

    return tuple(int(x) for x in m.group(1).split("."))


def convert(docx_path: Path, output_dir: Path | None = None) -> str:
    """Convert a .docx file to Markdown text via Pandoc.

    Args:
        docx_path: Path to the .docx file.
        output_dir: Directory for --extract-media. If None, uses docx_path.parent.

    Returns:
        The converted Markdown text.

    Raises:
        PandocNotFoundError: If pandoc is not installed.
        PandocVersionError: If pandoc version < 2.0.
    """
    version = get_version()

    if version[0] < 2:
        raise PandocVersionError(
            f"pandoc >= 2.0 required, found {'.'.join(str(v) for v in version)}"
        )

    # Calculate extract-media path
    media_dir = (output_dir if output_dir is not None else docx_path.parent) / "media"

    # Write to a temp file, then read back
    with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        # Use GFM (GitHub Flavored Markdown) for best table rendering:
        # - Simple tables → pipe format (| col1 | col2 |)
        # - Complex tables (rowspan/colspan) → HTML <table>
        # GFM uses ATX headings by default, so no heading flag needed.
        cmd = [
            "pandoc",
            str(docx_path),
            "-t", "gfm",
            "-o", str(tmp_path),
            "--wrap=none",
            f"--extract-media={media_dir}",
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        if result.returncode != 0:
            raise PandocNotFoundError(
                f"pandoc conversion failed: {result.stderr.strip()}"
            )

        return tmp_path.read_text(encoding="utf-8")
    finally:
        tmp_path.unlink(missing_ok=True)
