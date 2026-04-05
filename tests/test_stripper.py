"""Tests for stripper.py — numbering strip with mode branches and sync updates."""

from pathlib import Path

from feishu2md.models import HeadingInfo, LineInfo, ScanResult
from feishu2md.preprocessor import preprocess
from feishu2md.scanner import scan
from feishu2md.stripper import strip

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _heading_line(level: int, text: str, line_number: int = 1) -> LineInfo:
    """Create a LineInfo with heading metadata filled."""
    prefix = "#" * level
    line = LineInfo(
        line_number=line_number,
        raw_text=f"{prefix} {text}",
        heading_level=level,
        heading_text=text,
    )
    return line


def _scan_result(lines: list[LineInfo], is_valid: bool = False) -> ScanResult:
    """Build a ScanResult from heading lines."""
    headings = []
    min_level = 6
    for i, line in enumerate(lines):
        if line.heading_level is not None:
            headings.append(HeadingInfo(
                line_index=i,
                level=line.heading_level,
                title_text=line.heading_text,
                suspected_number=None,
            ))
            if line.heading_level < min_level:
                min_level = line.heading_level
    if not headings:
        min_level = 1
    return ScanResult(headings=headings, min_level=min_level, is_valid_sequence=is_valid)


# ─── mode='none' ─────────────────────────────────────────────────────────────


class TestModeNone:

    def test_returns_unchanged(self):
        line = _heading_line(1, "1 Title")
        lines = [line]
        sr = _scan_result(lines, is_valid=True)
        result_lines, result_sr, warnings = strip(lines, sr, "none")
        assert result_lines[0].heading_text == "1 Title"
        assert result_lines[0].raw_text == "# 1 Title"
        assert result_sr.headings[0].title_text == "1 Title"
        assert warnings == []

    def test_chinese_not_stripped(self):
        line = _heading_line(1, "一、标题")
        lines = [line]
        sr = _scan_result(lines)
        strip(lines, sr, "none")
        assert lines[0].heading_text == "一、标题"


# ─── mode='force' ────────────────────────────────────────────────────────────


class TestModeForce:

    def test_strips_numeric(self):
        line = _heading_line(1, "1 Title")
        lines = [line]
        sr = _scan_result(lines)
        strip(lines, sr, "force")
        assert lines[0].heading_text == "Title"

    def test_strips_dotted_numeric(self):
        line = _heading_line(2, "1.1 Title")
        lines = [line]
        sr = _scan_result(lines)
        strip(lines, sr, "force")
        assert lines[0].heading_text == "Title"

    def test_strips_deep_dotted(self):
        line = _heading_line(3, "1.1.1 Title")
        lines = [line]
        sr = _scan_result(lines)
        strip(lines, sr, "force")
        assert lines[0].heading_text == "Title"

    def test_strips_chinese(self):
        line = _heading_line(1, "一、标题")
        lines = [line]
        sr = _scan_result(lines)
        strip(lines, sr, "force")
        assert lines[0].heading_text == "标题"

    def test_strips_chinese_paren(self):
        line = _heading_line(1, "（一）标题")
        lines = [line]
        sr = _scan_result(lines)
        strip(lines, sr, "force")
        assert lines[0].heading_text == "标题"

    def test_strips_paren_numeric(self):
        line = _heading_line(1, "(1) 标题")
        lines = [line]
        sr = _scan_result(lines)
        strip(lines, sr, "force")
        assert lines[0].heading_text == "标题"

    def test_strips_fullwidth_paren(self):
        line = _heading_line(1, "（3）标题")
        lines = [line]
        sr = _scan_result(lines)
        strip(lines, sr, "force")
        assert lines[0].heading_text == "标题"

    def test_strips_version_number(self):
        """Force mode strips even version numbers."""
        line = _heading_line(1, "1.0 概述")
        lines = [line]
        sr = _scan_result(lines)
        strip(lines, sr, "force")
        assert lines[0].heading_text == "概述"


# ─── mode='auto' — valid sequence ────────────────────────────────────────────


class TestModeAutoValid:

    def test_strips_all_when_valid(self):
        lines = [
            _heading_line(1, "1 Title"),
            _heading_line(2, "1.1 Sub"),
        ]
        sr = _scan_result(lines, is_valid=True)
        strip(lines, sr, "auto")
        assert lines[0].heading_text == "Title"
        assert lines[1].heading_text == "Sub"

    def test_strips_chinese_when_valid(self):
        line = _heading_line(1, "一、标题")
        lines = [line]
        sr = _scan_result(lines, is_valid=True)
        strip(lines, sr, "auto")
        assert lines[0].heading_text == "标题"


# ─── mode='auto' — invalid sequence ──────────────────────────────────────────


class TestModeAutoInvalid:

    def test_preserves_numeric_when_invalid(self):
        """Invalid sequence → numeric prefixes NOT stripped."""
        line = _heading_line(1, "1.0 概述")
        lines = [line]
        sr = _scan_result(lines, is_valid=False)
        strip(lines, sr, "auto")
        assert lines[0].heading_text == "1.0 概述"

    def test_strips_chinese_when_invalid(self):
        """Invalid sequence → Chinese numbering STILL stripped."""
        line = _heading_line(1, "一、标题")
        lines = [line]
        sr = _scan_result(lines, is_valid=False)
        strip(lines, sr, "auto")
        assert lines[0].heading_text == "标题"

    def test_strips_chinese_paren_when_invalid(self):
        line = _heading_line(1, "（二）标题")
        lines = [line]
        sr = _scan_result(lines, is_valid=False)
        strip(lines, sr, "auto")
        assert lines[0].heading_text == "标题"

    def test_preserves_version_title(self):
        line = _heading_line(1, "2.0 Release Notes")
        lines = [line]
        sr = _scan_result(lines, is_valid=False)
        strip(lines, sr, "auto")
        assert lines[0].heading_text == "2.0 Release Notes"


# ─── mode='strip_only' ───────────────────────────────────────────────────────


class TestModeStripOnly:

    def test_same_as_auto_valid(self):
        line = _heading_line(1, "1 Title")
        lines = [line]
        sr = _scan_result(lines, is_valid=True)
        strip(lines, sr, "strip_only")
        assert lines[0].heading_text == "Title"

    def test_same_as_auto_invalid(self):
        line = _heading_line(1, "1.0 概述")
        lines = [line]
        sr = _scan_result(lines, is_valid=False)
        strip(lines, sr, "strip_only")
        assert lines[0].heading_text == "1.0 概述"


# ─── 三处同步更新 ────────────────────────────────────────────────────────────


class TestSyncUpdates:

    def test_heading_text_updated(self):
        line = _heading_line(2, "1.1 Title")
        lines = [line]
        sr = _scan_result(lines, is_valid=True)
        strip(lines, sr, "auto")
        assert lines[0].heading_text == "Title"

    def test_raw_text_updated(self):
        line = _heading_line(2, "1.1 Title")
        lines = [line]
        sr = _scan_result(lines, is_valid=True)
        strip(lines, sr, "auto")
        assert lines[0].raw_text == "## Title"

    def test_heading_info_title_text_updated(self):
        line = _heading_line(2, "1.1 Title")
        lines = [line]
        sr = _scan_result(lines, is_valid=True)
        strip(lines, sr, "auto")
        assert sr.headings[0].title_text == "Title"

    def test_all_three_in_sync(self):
        line = _heading_line(3, "1.1.1 Deep")
        lines = [line]
        sr = _scan_result(lines, is_valid=True)
        strip(lines, sr, "auto")
        assert lines[0].heading_text == "Deep"
        assert lines[0].raw_text == "### Deep"
        assert sr.headings[0].title_text == "Deep"

    def test_no_change_when_no_match(self):
        line = _heading_line(1, "Plain Title")
        lines = [line]
        sr = _scan_result(lines, is_valid=True)
        strip(lines, sr, "auto")
        assert lines[0].heading_text == "Plain Title"
        assert lines[0].raw_text == "# Plain Title"
        assert sr.headings[0].title_text == "Plain Title"


# ─── Markdown 格式保护 ───────────────────────────────────────────────────────


class TestMarkdownFormatProtection:

    def test_bold_title_preserved(self):
        line = _heading_line(2, "1.1 **加粗标题**")
        lines = [line]
        sr = _scan_result(lines, is_valid=True)
        strip(lines, sr, "auto")
        assert lines[0].heading_text == "**加粗标题**"
        assert lines[0].raw_text == "## **加粗标题**"

    def test_link_title_preserved(self):
        line = _heading_line(2, "1.1 [链接标题](url)")
        lines = [line]
        sr = _scan_result(lines, is_valid=True)
        strip(lines, sr, "auto")
        assert lines[0].heading_text == "[链接标题](url)"

    def test_inline_code_preserved(self):
        line = _heading_line(2, "1.1 `code` title")
        lines = [line]
        sr = _scan_result(lines, is_valid=True)
        strip(lines, sr, "auto")
        assert lines[0].heading_text == "`code` title"

    def test_number_inside_format_not_stripped(self):
        """Numbers inside markdown formatting should not be stripped."""
        line = _heading_line(1, "**1.1 加粗内容**")
        lines = [line]
        sr = _scan_result(lines, is_valid=True)
        strip(lines, sr, "auto")
        # ** starts the text, regex anchored at ^ won't match inside **
        assert lines[0].heading_text == "**1.1 加粗内容**"


# ─── 不被误杀的标题 ──────────────────────────────────────────────────────────


class TestNoFalsePositives:

    def test_year_title_preserved_when_invalid(self):
        line = _heading_line(1, "2024 年度总结")
        lines = [line]
        sr = _scan_result(lines, is_valid=False)
        strip(lines, sr, "auto")
        assert lines[0].heading_text == "2024 年度总结"

    def test_3d_title_preserved(self):
        """'3D 建模规范' — doesn't match numeric pattern (D after digit)."""
        line = _heading_line(1, "3D 建模规范")
        lines = [line]
        sr = _scan_result(lines, is_valid=True)
        strip(lines, sr, "auto")
        assert lines[0].heading_text == "3D 建模规范"

    def test_5g_title_preserved(self):
        line = _heading_line(1, "5G 技术白皮书")
        lines = [line]
        sr = _scan_result(lines, is_valid=True)
        strip(lines, sr, "auto")
        assert lines[0].heading_text == "5G 技术白皮书"

    def test_non_heading_lines_untouched(self):
        """Non-heading lines should not be modified at all."""
        normal = LineInfo(line_number=1, raw_text="1.1 normal text")
        heading = _heading_line(1, "1 Title", line_number=2)
        lines = [normal, heading]
        sr = _scan_result(lines, is_valid=True)
        strip(lines, sr, "auto")
        assert lines[0].raw_text == "1.1 normal text"  # untouched
        assert lines[1].heading_text == "Title"


# ─── 多标题文档 ──────────────────────────────────────────────────────────────


class TestMultipleHeadings:

    def test_full_document_strip(self):
        lines = [
            _heading_line(1, "1 产品概述", line_number=1),
            LineInfo(line_number=2, raw_text="正文"),
            _heading_line(2, "1.1 功能设计", line_number=3),
            _heading_line(3, "1.1.1 交互逻辑", line_number=5),
            _heading_line(3, "1.1.2 视觉规范", line_number=7),
            _heading_line(2, "1.2 技术方案", line_number=9),
            _heading_line(1, "2 项目计划", line_number=11),
        ]
        sr = _scan_result(lines, is_valid=True)
        strip(lines, sr, "auto")

        texts = [l.heading_text for l in lines if l.heading_level is not None]
        assert texts == ["产品概述", "功能设计", "交互逻辑", "视觉规范", "技术方案", "项目计划"]

        raw_texts = [l.raw_text for l in lines if l.heading_level is not None]
        assert raw_texts == [
            "# 产品概述", "## 功能设计", "### 交互逻辑",
            "### 视觉规范", "## 技术方案", "# 项目计划",
        ]

    def test_mixed_chinese_and_numeric(self):
        lines = [
            _heading_line(1, "一、概述"),
            _heading_line(2, "1.1 功能"),
        ]
        sr = _scan_result(lines, is_valid=False)
        strip(lines, sr, "auto")
        # Invalid sequence → only Chinese stripped
        assert lines[0].heading_text == "概述"
        assert lines[1].heading_text == "1.1 功能"  # numeric preserved


# ─── 返回值结构 ──────────────────────────────────────────────────────────────


class TestReturnStructure:

    def test_returns_tuple_of_three(self):
        lines = [_heading_line(1, "Title")]
        sr = _scan_result(lines)
        result = strip(lines, sr, "auto")
        assert isinstance(result, tuple)
        assert len(result) == 3

    def test_returns_same_lines_object(self):
        """strip modifies in-place, returns the same list object."""
        lines = [_heading_line(1, "1 Title")]
        sr = _scan_result(lines, is_valid=True)
        result_lines, _, _ = strip(lines, sr, "auto")
        assert result_lines is lines

    def test_returns_same_scan_result_object(self):
        lines = [_heading_line(1, "1 Title")]
        sr = _scan_result(lines, is_valid=True)
        _, result_sr, _ = strip(lines, sr, "auto")
        assert result_sr is sr

    def test_warnings_list(self):
        lines = [_heading_line(1, "Title")]
        sr = _scan_result(lines)
        _, _, warnings = strip(lines, sr, "auto")
        assert isinstance(warnings, list)


# ─── Fixture 集成测试 ────────────────────────────────────────────────────────


class TestFixtureFormattedHeadings:

    def test_force_strip_formatted(self):
        """Full pipeline: preprocess → scan → strip(force) on formatted_headings.md."""
        content = (FIXTURES / "formatted_headings.md").read_text(encoding="utf-8")
        lines = preprocess(content)
        sr, _ = scan(lines)
        strip(lines, sr, "force")

        heading_texts = [l.heading_text for l in lines if l.heading_level is not None]
        # Numeric prefixes stripped, Markdown formatting preserved
        assert "**加粗的一级标题**" in heading_texts
        assert "[链接标题](https://example.com)" in heading_texts
        assert "`代码` 标题" in heading_texts
        assert "普通标题" in heading_texts
        # Chinese numbering also stripped
        assert "中文编号标题" in heading_texts
        assert "中文括号编号" in heading_texts

    def test_auto_strip_formatted(self):
        """Auto mode on formatted_headings.md — has valid sequence."""
        content = (FIXTURES / "formatted_headings.md").read_text(encoding="utf-8")
        lines = preprocess(content)
        sr, _ = scan(lines)
        # The document has numbered headings (1, 1.1, 1.1.1, 1.2, 2) — valid sequence
        strip(lines, sr, "auto")

        heading_texts = [l.heading_text for l in lines if l.heading_level is not None]
        assert "**加粗的一级标题**" in heading_texts
        # Chinese always stripped regardless
        assert "中文编号标题" in heading_texts
