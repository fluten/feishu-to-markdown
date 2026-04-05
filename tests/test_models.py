"""Tests for models.py — shared data structures and exceptions."""

import dataclasses

import pytest

from feishu2md.models import (
    Feishu2MdError,
    HeadingInfo,
    InputError,
    LineInfo,
    PandocNotFoundError,
    PandocVersionError,
    ScanResult,
    Warning,
    WriteError,
)


# ─── LineInfo ─────────────────────────────────────────────────────────────────


class TestLineInfo:

    def test_required_fields(self):
        line = LineInfo(line_number=1, raw_text="hello")
        assert line.line_number == 1
        assert line.raw_text == "hello"

    def test_default_values(self):
        line = LineInfo(line_number=1, raw_text="")
        assert line.is_protected is False
        assert line.is_blockquote is False
        assert line.heading_level is None
        assert line.heading_text is None

    def test_all_fields(self):
        line = LineInfo(
            line_number=5,
            raw_text="## 标题",
            is_protected=False,
            is_blockquote=False,
            heading_level=2,
            heading_text="标题",
        )
        assert line.heading_level == 2
        assert line.heading_text == "标题"

    def test_mutable(self):
        """LineInfo fields must be mutable (stripper/numbering modify in-place)."""
        line = LineInfo(line_number=1, raw_text="# old")
        line.raw_text = "# new"
        line.heading_text = "new"
        assert line.raw_text == "# new"
        assert line.heading_text == "new"

    def test_heading_level_none_means_not_heading(self):
        line = LineInfo(line_number=1, raw_text="普通文本")
        assert line.heading_level is None
        assert line.heading_text is None

    def test_is_dataclass(self):
        assert dataclasses.is_dataclass(LineInfo)

    def test_equality(self):
        a = LineInfo(line_number=1, raw_text="# hi")
        b = LineInfo(line_number=1, raw_text="# hi")
        assert a == b

    def test_inequality(self):
        a = LineInfo(line_number=1, raw_text="# hi")
        b = LineInfo(line_number=2, raw_text="# hi")
        assert a != b


# ─── HeadingInfo ──────────────────────────────────────────────────────────────


class TestHeadingInfo:

    def test_all_fields(self):
        h = HeadingInfo(line_index=3, level=2, title_text="功能设计", suspected_number="1.1")
        assert h.line_index == 3
        assert h.level == 2
        assert h.title_text == "功能设计"
        assert h.suspected_number == "1.1"

    def test_no_suspected_number(self):
        h = HeadingInfo(line_index=0, level=1, title_text="概述", suspected_number=None)
        assert h.suspected_number is None

    def test_mutable(self):
        """title_text must be mutable (stripper updates it)."""
        h = HeadingInfo(line_index=0, level=1, title_text="1 旧标题", suspected_number="1")
        h.title_text = "旧标题"
        assert h.title_text == "旧标题"

    def test_is_dataclass(self):
        assert dataclasses.is_dataclass(HeadingInfo)

    def test_equality(self):
        a = HeadingInfo(line_index=0, level=1, title_text="标题", suspected_number=None)
        b = HeadingInfo(line_index=0, level=1, title_text="标题", suspected_number=None)
        assert a == b


# ─── ScanResult ───────────────────────────────────────────────────────────────


class TestScanResult:

    def test_all_fields(self):
        headings = [
            HeadingInfo(line_index=0, level=1, title_text="标题", suspected_number=None),
        ]
        result = ScanResult(headings=headings, min_level=1, is_valid_sequence=False)
        assert len(result.headings) == 1
        assert result.min_level == 1
        assert result.is_valid_sequence is False

    def test_empty_headings(self):
        result = ScanResult(headings=[], min_level=0, is_valid_sequence=False)
        assert result.headings == []

    def test_valid_sequence_true(self):
        result = ScanResult(headings=[], min_level=1, is_valid_sequence=True)
        assert result.is_valid_sequence is True

    def test_is_dataclass(self):
        assert dataclasses.is_dataclass(ScanResult)

    def test_headings_list_appendable(self):
        """headings list must support append (scanner builds it incrementally)."""
        result = ScanResult(headings=[], min_level=1, is_valid_sequence=False)
        result.headings.append(
            HeadingInfo(line_index=0, level=1, title_text="新标题", suspected_number=None)
        )
        assert len(result.headings) == 1


# ─── Warning ──────────────────────────────────────────────────────────────────


class TestWarning:

    def test_all_fields(self):
        w = Warning(line_number=42, message="heading level jumped from H1 to H3")
        assert w.line_number == 42
        assert w.message == "heading level jumped from H1 to H3"

    def test_is_dataclass(self):
        assert dataclasses.is_dataclass(Warning)

    def test_chinese_message(self):
        w = Warning(line_number=1, message="标题层级跳跃")
        assert w.message == "标题层级跳跃"


# ─── 异常层级 ─────────────────────────────────────────────────────────────────


class TestExceptions:

    def test_base_is_exception(self):
        assert issubclass(Feishu2MdError, Exception)

    def test_input_error_inherits(self):
        assert issubclass(InputError, Feishu2MdError)

    def test_pandoc_not_found_inherits(self):
        assert issubclass(PandocNotFoundError, Feishu2MdError)

    def test_pandoc_version_inherits(self):
        assert issubclass(PandocVersionError, Feishu2MdError)

    def test_write_error_inherits(self):
        assert issubclass(WriteError, Feishu2MdError)

    def test_catch_base_catches_all(self):
        """All subclass exceptions should be catchable via Feishu2MdError."""
        for exc_class in [InputError, PandocNotFoundError, PandocVersionError, WriteError]:
            with pytest.raises(Feishu2MdError):
                raise exc_class("test")

    def test_exception_message(self):
        e = InputError("file not found: test.md")
        assert str(e) == "file not found: test.md"

    def test_exceptions_not_siblings(self):
        """PandocNotFoundError and InputError are independent branches."""
        assert not issubclass(PandocNotFoundError, InputError)
        assert not issubclass(InputError, WriteError)


# ─── 不存在 ProcessedLine ────────────────────────────────────────────────────


class TestNoProcessedLine:

    def test_processed_line_not_defined(self):
        """ProcessedLine was removed — verify it doesn't exist."""
        import feishu2md.models as m
        assert not hasattr(m, "ProcessedLine")


# ─── 模块导出完整性 ──────────────────────────────────────────────────────────


class TestModuleExports:

    def test_all_expected_names_exist(self):
        """Verify every expected name is importable from models."""
        import feishu2md.models as m
        expected = [
            "LineInfo", "HeadingInfo", "ScanResult", "Warning",
            "Feishu2MdError", "InputError", "PandocNotFoundError",
            "PandocVersionError", "WriteError",
        ]
        for name in expected:
            assert hasattr(m, name), f"{name} missing from models.py"

    def test_no_unexpected_public_classes(self):
        """No extra public dataclass or exception beyond what SPEC defines."""
        import feishu2md.models as m
        expected = {
            "LineInfo", "HeadingInfo", "ScanResult", "Warning",
            "Feishu2MdError", "InputError", "PandocNotFoundError",
            "PandocVersionError", "WriteError",
        }
        public_classes = {
            name for name, obj in vars(m).items()
            if isinstance(obj, type) and not name.startswith("_")
        }
        assert public_classes == expected


# ─── 异常策略场景（对照 CLAUDE.md） ──────────────────────────────────────────


class TestExceptionUsagePattern:

    def test_input_error_caught_as_base(self):
        """Simulates __main__.py catch pattern: InputError → exit 1."""
        exit_code = 0
        try:
            raise InputError("file not found: test.md")
        except Feishu2MdError:
            exit_code = 1
        assert exit_code == 1

    def test_pandoc_errors_caught_as_base(self):
        """Simulates __main__.py catch pattern: PandocNotFoundError → exit 2."""
        for exc_class in [PandocNotFoundError, PandocVersionError]:
            exit_code = 0
            try:
                raise exc_class("pandoc missing")
            except (PandocNotFoundError, PandocVersionError):
                exit_code = 2
            assert exit_code == 2

    def test_write_error_caught_as_base(self):
        """Simulates __main__.py catch pattern: WriteError → exit 1."""
        exit_code = 0
        try:
            raise WriteError("cannot write to /tmp/out.md")
        except Feishu2MdError:
            exit_code = 1
        assert exit_code == 1
