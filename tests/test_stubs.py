"""Tests for module stubs — verify function signatures and imports (Phase 1)."""

import inspect
from pathlib import Path

import pytest


class TestPreprocessorStub:

    def test_importable(self):
        from feishu2md import preprocessor
        assert hasattr(preprocessor, "preprocess")

    def test_signature(self):
        from feishu2md.preprocessor import preprocess
        sig = inspect.signature(preprocess)
        params = list(sig.parameters.keys())
        assert params == ["content"]

    def test_returns_none_for_now(self):
        from feishu2md.preprocessor import preprocess
        assert preprocess("") is None


class TestScannerStub:

    def test_importable(self):
        from feishu2md import scanner
        assert hasattr(scanner, "scan")

    def test_signature(self):
        from feishu2md.scanner import scan
        sig = inspect.signature(scan)
        params = list(sig.parameters.keys())
        assert params == ["lines"]

    def test_returns_none_for_now(self):
        from feishu2md.scanner import scan
        assert scan([]) is None


class TestStripperStub:

    def test_importable(self):
        from feishu2md import stripper
        assert hasattr(stripper, "strip")

    def test_signature(self):
        from feishu2md.stripper import strip
        sig = inspect.signature(strip)
        params = list(sig.parameters.keys())
        assert params == ["lines", "scan_result", "mode"]

    def test_returns_none_for_now(self):
        from feishu2md.stripper import strip
        from feishu2md.models import ScanResult
        result = ScanResult(headings=[], min_level=1, is_valid_sequence=False)
        assert strip([], result, "auto") is None


class TestNumberingStub:

    def test_importable(self):
        from feishu2md import numbering
        assert hasattr(numbering, "generate")

    def test_signature(self):
        from feishu2md.numbering import generate
        sig = inspect.signature(generate)
        params = list(sig.parameters.keys())
        assert params == ["lines", "scan_result", "max_level"]

    def test_returns_none_for_now(self):
        from feishu2md.numbering import generate
        from feishu2md.models import ScanResult
        result = ScanResult(headings=[], min_level=1, is_valid_sequence=False)
        assert generate([], result, 3) is None


class TestPandocStub:

    def test_importable(self):
        from feishu2md import pandoc
        assert hasattr(pandoc, "convert")

    def test_signature(self):
        from feishu2md.pandoc import convert
        sig = inspect.signature(convert)
        params = list(sig.parameters.keys())
        assert params == ["docx_path", "output_dir"]

    def test_output_dir_default_none(self):
        from feishu2md.pandoc import convert
        sig = inspect.signature(convert)
        assert sig.parameters["output_dir"].default is None

    def test_returns_none_for_now(self):
        from feishu2md.pandoc import convert
        assert convert(Path("dummy.docx")) is None


class TestWriterStub:

    def test_importable(self):
        from feishu2md import writer
        assert hasattr(writer, "write")

    def test_signature(self):
        from feishu2md.writer import write
        sig = inspect.signature(write)
        params = list(sig.parameters.keys())
        assert params == ["lines", "output", "inplace", "backup", "input_path"]

    def test_input_path_default_none(self):
        from feishu2md.writer import write
        sig = inspect.signature(write)
        assert sig.parameters["input_path"].default is None

    def test_returns_none_for_now(self):
        from feishu2md.writer import write
        assert write([], None, False, True) is None


class TestConftestFixture:

    def test_fixtures_dir_exists(self, fixtures_dir):
        assert fixtures_dir.is_dir()

    def test_fixtures_dir_is_correct_path(self, fixtures_dir):
        assert fixtures_dir.name == "fixtures"
        assert fixtures_dir.parent.name == "tests"


class TestHelpOutput:

    def test_help_runs_successfully(self):
        import subprocess
        import sys
        result = subprocess.run(
            [sys.executable, "-m", "feishu2md", "--help"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        assert result.returncode == 0
        assert "feishu2md" in result.stdout
