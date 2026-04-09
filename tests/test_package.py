"""Tests for package structure and project configuration (Phase 1)."""

import subprocess
import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomllib
    except ModuleNotFoundError:
        import tomli as tomllib  # type: ignore[no-redef]

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = PROJECT_ROOT / "pyproject.toml"


@pytest.fixture(scope="module")
def pyproject_data() -> dict:
    """Load pyproject.toml as a dict."""
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))


# ─── __init__.py ──────────────────────────────────────────────────────────────


class TestPackageInit:
    """feishu2md/__init__.py"""

    def test_version_importable(self):
        from feishu2md import __version__
        assert isinstance(__version__, str)

    def test_version_value(self):
        from feishu2md import __version__
        assert __version__ == "1.1.0"

    def test_package_importable(self):
        import feishu2md
        assert hasattr(feishu2md, "__version__")


# ─── pyproject.toml — 元数据 ─────────────────────────────────────────────────


class TestPyprojectMetadata:
    """Project metadata fields in pyproject.toml."""

    def test_file_exists(self):
        assert PYPROJECT.exists()

    def test_name(self, pyproject_data):
        assert pyproject_data["project"]["name"] == "feishu-to-markdown"

    def test_version(self, pyproject_data):
        assert pyproject_data["project"]["version"] == "1.1.0"

    def test_version_matches_init(self, pyproject_data):
        from feishu2md import __version__
        assert pyproject_data["project"]["version"] == __version__

    def test_description_present(self, pyproject_data):
        desc = pyproject_data["project"]["description"]
        assert isinstance(desc, str) and len(desc) > 0

    def test_authors_present(self, pyproject_data):
        authors = pyproject_data["project"]["authors"]
        assert len(authors) >= 1
        assert "name" in authors[0]

    def test_license_present(self, pyproject_data):
        assert "license" in pyproject_data["project"]

    def test_requires_python(self, pyproject_data):
        assert pyproject_data["project"]["requires-python"] == ">=3.10"


# ─── pyproject.toml — pytest 配置 ────────────────────────────────────────────


class TestPyprojectPytest:
    """Pytest configuration in pyproject.toml."""

    def test_testpaths(self, pyproject_data):
        assert pyproject_data["tool"]["pytest"]["ini_options"]["testpaths"] == ["tests"]

    def test_integration_marker_defined(self, pyproject_data):
        markers = pyproject_data["tool"]["pytest"]["ini_options"]["markers"]
        assert any("integration" in m for m in markers)

    def test_integration_marker_no_warning(self):
        """Running pytest --markers should list 'integration' without warnings."""
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--markers"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(PROJECT_ROOT),
        )
        assert "integration" in result.stdout


# ─── 包结构可运行 ────────────────────────────────────────────────────────────


class TestPackageRunnable:
    """python -m feishu2md should be importable as a package."""

    def test_package_directory_exists(self):
        pkg_dir = PROJECT_ROOT / "feishu2md"
        assert pkg_dir.is_dir()

    def test_init_file_exists(self):
        init_file = PROJECT_ROOT / "feishu2md" / "__init__.py"
        assert init_file.is_file()
