"""Tests for scanner.py — heading identification, metadata population, HeadingInfo creation."""

from pathlib import Path

from feishu2md.models import LineInfo, ScanResult
from feishu2md.preprocessor import preprocess
from feishu2md.scanner import scan

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _make_lines(*raw_texts: str, **overrides) -> list[LineInfo]:
    """Helper to create LineInfo list from raw text strings."""
    lines = []
    for i, text in enumerate(raw_texts):
        line = LineInfo(line_number=i + 1, raw_text=text)
        lines.append(line)
    return lines


def _make_protected(*raw_texts: str) -> list[LineInfo]:
    """Helper: all lines are protected."""
    return [LineInfo(line_number=i + 1, raw_text=t, is_protected=True)
            for i, t in enumerate(raw_texts)]


def _make_blockquote(*raw_texts: str) -> list[LineInfo]:
    """Helper: all lines are blockquote."""
    return [LineInfo(line_number=i + 1, raw_text=t, is_blockquote=True)
            for i, t in enumerate(raw_texts)]


# ─── 标题行识别 ──────────────────────────────────────────────────────────────


class TestHeadingIdentification:

    def test_h1(self):
        lines = _make_lines("# Title")
        result, _ = scan(lines)
        assert len(result.headings) == 1
        assert result.headings[0].level == 1

    def test_h2(self):
        lines = _make_lines("## Title")
        result, _ = scan(lines)
        assert result.headings[0].level == 2

    def test_h3(self):
        lines = _make_lines("### Title")
        result, _ = scan(lines)
        assert result.headings[0].level == 3

    def test_h4(self):
        lines = _make_lines("#### Title")
        result, _ = scan(lines)
        assert result.headings[0].level == 4

    def test_h5(self):
        lines = _make_lines("##### Title")
        result, _ = scan(lines)
        assert result.headings[0].level == 5

    def test_h6(self):
        lines = _make_lines("###### Title")
        result, _ = scan(lines)
        assert result.headings[0].level == 6

    def test_h7_not_heading(self):
        """####### (7 hashes) is not a valid heading."""
        lines = _make_lines("####### Title")
        result, _ = scan(lines)
        assert len(result.headings) == 0

    def test_no_space_not_heading(self):
        """#tag (no space after #) is not a heading."""
        lines = _make_lines("#tag")
        result, _ = scan(lines)
        assert len(result.headings) == 0

    def test_empty_heading_not_identified(self):
        """'# ' with nothing after is not identified as heading."""
        lines = _make_lines("# ")
        result, _ = scan(lines)
        assert len(result.headings) == 0

    def test_empty_heading_with_spaces(self):
        """'#   ' (only spaces) is an empty heading — should not be identified."""
        lines = _make_lines("#   ")
        result, _ = scan(lines)
        assert len(result.headings) == 0

    def test_heading_with_only_whitespace_after_hash_space(self):
        """'#  x' should match — there's content after space."""
        lines = _make_lines("#  x")
        result, _ = scan(lines)
        assert len(result.headings) == 1
        assert result.headings[0].title_text == "x"

    def test_multiple_headings(self):
        lines = _make_lines("# A", "text", "## B", "### C")
        result, _ = scan(lines)
        assert len(result.headings) == 3
        levels = [h.level for h in result.headings]
        assert levels == [1, 2, 3]

    def test_normal_text_not_heading(self):
        lines = _make_lines("normal text", "another line")
        result, _ = scan(lines)
        assert len(result.headings) == 0


# ─── 排除受保护区域和 blockquote ─────────────────────────────────────────────


class TestProtectedAndBlockquote:

    def test_skip_protected_lines(self):
        lines = _make_protected("# Protected heading")
        result, _ = scan(lines)
        assert len(result.headings) == 0

    def test_skip_blockquote_lines(self):
        lines = _make_blockquote("> # Quoted heading")
        result, _ = scan(lines)
        assert len(result.headings) == 0

    def test_mixed_protected_and_normal(self):
        lines = [
            LineInfo(line_number=1, raw_text="# Normal", is_protected=False),
            LineInfo(line_number=2, raw_text="# Protected", is_protected=True),
            LineInfo(line_number=3, raw_text="## Also normal", is_protected=False),
        ]
        result, _ = scan(lines)
        assert len(result.headings) == 2
        assert result.headings[0].title_text == "Normal"
        assert result.headings[1].title_text == "Also normal"

    def test_protected_heading_metadata_not_filled(self):
        """Protected lines should NOT have heading_level filled."""
        lines = _make_protected("# Should not be filled")
        scan(lines)
        assert lines[0].heading_level is None
        assert lines[0].heading_text is None

    def test_blockquote_heading_metadata_not_filled(self):
        lines = _make_blockquote("> # Quoted")
        scan(lines)
        assert lines[0].heading_level is None


# ─── LineInfo 元数据填充 ─────────────────────────────────────────────────────


class TestLineInfoMetadata:

    def test_heading_level_filled(self):
        lines = _make_lines("# Title")
        scan(lines)
        assert lines[0].heading_level == 1

    def test_heading_text_filled(self):
        lines = _make_lines("## My Section")
        scan(lines)
        assert lines[0].heading_text == "My Section"

    def test_non_heading_metadata_unchanged(self):
        lines = _make_lines("normal text")
        scan(lines)
        assert lines[0].heading_level is None
        assert lines[0].heading_text is None

    def test_heading_text_preserves_formatting(self):
        """Markdown formatting in heading text should be preserved."""
        lines = _make_lines("## **Bold Title**")
        scan(lines)
        assert lines[0].heading_text == "**Bold Title**"

    def test_heading_text_with_inline_code(self):
        lines = _make_lines("### `code` in title")
        scan(lines)
        assert lines[0].heading_text == "`code` in title"

    def test_heading_text_chinese(self):
        lines = _make_lines("# 产品概述")
        scan(lines)
        assert lines[0].heading_text == "产品概述"

    def test_multiple_spaces_after_hash(self):
        """'##  Title' — extra spaces consumed, text is stripped."""
        lines = _make_lines("##  Title")
        scan(lines)
        assert lines[0].heading_level == 2
        assert lines[0].heading_text == "Title"

    def test_raw_text_not_modified(self):
        """Scanner must NOT modify raw_text."""
        lines = _make_lines("## My Title")
        scan(lines)
        assert lines[0].raw_text == "## My Title"

    def test_heading_text_trailing_whitespace_stripped(self):
        """Trailing whitespace in heading text is stripped."""
        lines = _make_lines("# Title   ")
        scan(lines)
        assert lines[0].heading_text == "Title"
        assert lines[0].raw_text == "# Title   "  # raw_text untouched


# ─── HeadingInfo 列表创建 ────────────────────────────────────────────────────


class TestHeadingInfoCreation:

    def test_line_index_is_list_index(self):
        """line_index should be the index in lines list, not line_number."""
        lines = _make_lines("text", "# First", "more text", "## Second")
        result, _ = scan(lines)
        assert result.headings[0].line_index == 1
        assert result.headings[1].line_index == 3

    def test_line_index_not_line_number(self):
        """Explicitly verify line_index != line_number when they differ."""
        lines = [
            LineInfo(line_number=10, raw_text="# Title"),  # line_number=10, index=0
        ]
        result, _ = scan(lines)
        assert result.headings[0].line_index == 0  # index, not line_number

    def test_title_text_matches_heading_text(self):
        lines = _make_lines("## Hello World")
        result, _ = scan(lines)
        assert result.headings[0].title_text == "Hello World"
        assert result.headings[0].title_text == lines[1 - 1].heading_text

    def test_level_matches_heading_level(self):
        lines = _make_lines("### Deep")
        result, _ = scan(lines)
        assert result.headings[0].level == 3
        assert result.headings[0].level == lines[0].heading_level

    def test_suspected_number_extracted(self):
        lines = _make_lines("# 1 Title", "## 1.1 Sub")
        result, _ = scan(lines)
        assert result.headings[0].suspected_number == "1"
        assert result.headings[1].suspected_number == "1.1"

    def test_suspected_number_none_when_no_number(self):
        lines = _make_lines("# Title without number")
        result, _ = scan(lines)
        assert result.headings[0].suspected_number is None

    def test_empty_document_no_headings(self):
        lines = _make_lines("")
        result, _ = scan(lines)
        assert result.headings == []

    def test_no_headings_document(self):
        lines = _make_lines("just text", "more text", "")
        result, _ = scan(lines)
        assert result.headings == []


# ─── min_level 检测 ──────────────────────────────────────────────────────────


class TestMinLevel:

    def test_single_h1(self):
        lines = _make_lines("# Title")
        result, _ = scan(lines)
        assert result.min_level == 1

    def test_single_h2(self):
        lines = _make_lines("## Title")
        result, _ = scan(lines)
        assert result.min_level == 2

    def test_h2_and_h3(self):
        lines = _make_lines("## A", "### B")
        result, _ = scan(lines)
        assert result.min_level == 2

    def test_h3_only(self):
        lines = _make_lines("### A", "### B")
        result, _ = scan(lines)
        assert result.min_level == 3

    def test_mixed_levels(self):
        lines = _make_lines("### C", "# A", "## B")
        result, _ = scan(lines)
        assert result.min_level == 1

    def test_no_headings_min_level_default(self):
        lines = _make_lines("no headings")
        result, _ = scan(lines)
        assert result.min_level == 1  # default when no headings


# ─── ScanResult 结构 ─────────────────────────────────────────────────────────


class TestScanResultStructure:

    def test_returns_tuple(self):
        lines = _make_lines("# A")
        result = scan(lines)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_result_is_scan_result(self):
        lines = _make_lines("# A")
        result, warnings = scan(lines)
        assert isinstance(result, ScanResult)
        assert isinstance(warnings, list)

    def test_warnings_empty_when_no_numbers(self):
        lines = _make_lines("# A", "## B")
        _, warnings = scan(lines)
        assert warnings == []

    def test_valid_sequence_true(self):
        lines = _make_lines("# 1 A", "## 1.1 B", "## 1.2 C", "# 2 D")
        result, _ = scan(lines)
        assert result.is_valid_sequence is True


# ─── 疑似编号提取 ────────────────────────────────────────────────────────────


class TestSuspectedNumberExtraction:

    def test_single_number(self):
        lines = _make_lines("# 1 Title")
        result, _ = scan(lines)
        assert result.headings[0].suspected_number == "1"

    def test_dotted_number(self):
        lines = _make_lines("## 1.1 Title")
        result, _ = scan(lines)
        assert result.headings[0].suspected_number == "1.1"

    def test_deep_dotted_number(self):
        lines = _make_lines("### 1.2.3 Title")
        result, _ = scan(lines)
        assert result.headings[0].suspected_number == "1.2.3"

    def test_no_number(self):
        lines = _make_lines("# Plain title")
        result, _ = scan(lines)
        assert result.headings[0].suspected_number is None

    def test_number_without_trailing_space_not_extracted(self):
        """'1.0概述' — no space after number, not a suspected numbering."""
        lines = _make_lines("# 1.0概述")
        result, _ = scan(lines)
        # regex requires \s+ after the number
        assert result.headings[0].suspected_number is None

    def test_version_number_extracted_as_suspected(self):
        """'1.0 概述' matches the regex — it's up to sequence validation to reject."""
        lines = _make_lines("# 1.0 概述")
        result, _ = scan(lines)
        assert result.headings[0].suspected_number == "1.0"

    def test_chinese_numbering_not_extracted(self):
        """Chinese numbering is NOT extracted as suspected_number (handled by stripper)."""
        lines = _make_lines("# 一、标题")
        result, _ = scan(lines)
        assert result.headings[0].suspected_number is None

    def test_paren_numbering_not_extracted(self):
        """Parenthesized numbering is NOT extracted (handled by stripper)."""
        lines = _make_lines("# (1) 标题")
        result, _ = scan(lines)
        assert result.headings[0].suspected_number is None

    def test_year_not_extracted(self):
        """'2024 年度总结' — 2024 is extracted as suspected number (sequence check rejects)."""
        lines = _make_lines("# 2024 年度总结")
        result, _ = scan(lines)
        assert result.headings[0].suspected_number == "2024"

    def test_3d_not_extracted(self):
        """'3D 建模' — '3D' doesn't match digit-only pattern."""
        lines = _make_lines("# 3D 建模")
        result, _ = scan(lines)
        # '3D' starts with digit but 'D' breaks \d+(\.\d+)* pattern
        # Actually regex is ^\d+(\.\d+)*\s+ — '3D 建模' → \d+ matches '3', then needs \s+
        # but next char is 'D', not space → no match
        assert result.headings[0].suspected_number is None


# ─── 序列合理性判断 ──────────────────────────────────────────────────────────


class TestSequenceValidity:

    def test_valid_simple_sequence(self):
        lines = _make_lines("# 1 A", "# 2 B", "# 3 C")
        result, _ = scan(lines)
        assert result.is_valid_sequence is True

    def test_valid_hierarchical_sequence(self):
        lines = _make_lines("# 1 A", "## 1.1 B", "## 1.2 C", "# 2 D", "## 2.1 E")
        result, _ = scan(lines)
        assert result.is_valid_sequence is True

    def test_valid_with_gaps(self):
        """Gaps are allowed: 1, 2, 4 is valid."""
        lines = _make_lines("# 1 A", "# 2 B", "# 4 C")
        result, _ = scan(lines)
        assert result.is_valid_sequence is True

    def test_invalid_out_of_order(self):
        """1, 5, 2 is out of order → invalid."""
        lines = _make_lines("# 1 A", "# 5 B", "# 2 C")
        result, _ = scan(lines)
        assert result.is_valid_sequence is False

    def test_invalid_parent_prefix_mismatch(self):
        """H2 '2.1' under H1 '1' → parent prefix mismatch."""
        lines = _make_lines("# 1 A", "## 2.1 B")
        result, _ = scan(lines)
        assert result.is_valid_sequence is False

    def test_valid_parent_prefix(self):
        """H2 '1.1' under H1 '1' → correct parent prefix."""
        lines = _make_lines("# 1 A", "## 1.1 B")
        result, _ = scan(lines)
        assert result.is_valid_sequence is True

    def test_invalid_less_than_50_percent(self):
        """Less than 50% have numbers → invalid."""
        lines = _make_lines("# 1 A", "# B", "# C", "# D")
        result, _ = scan(lines)
        assert result.is_valid_sequence is False

    def test_exactly_50_percent(self):
        """Exactly 50% → valid (>= 0.5)."""
        lines = _make_lines("# 1 A", "# 2 B", "# C", "# D")
        result, _ = scan(lines)
        assert result.is_valid_sequence is True

    def test_version_numbers_invalid(self):
        """'1.0 概述', '2.0 Release' — not a valid sequence (1.0 then 2.0 at same level)."""
        lines = _make_lines("# 1.0 概述", "## 2.0 Release Notes", "## 3.1 版本更新日志")
        result, _ = scan(lines)
        # 2.0 under 1.0: parent prefix '2' != '1.0' (or level mismatch)
        assert result.is_valid_sequence is False

    def test_no_headings_invalid(self):
        lines = _make_lines("no headings")
        result, _ = scan(lines)
        assert result.is_valid_sequence is False

    def test_no_numbered_headings_invalid(self):
        lines = _make_lines("# A", "## B")
        result, _ = scan(lines)
        assert result.is_valid_sequence is False

    def test_all_same_number_invalid(self):
        """1, 1, 1 — not increasing → invalid."""
        lines = _make_lines("# 1 A", "# 1 B", "# 1 C")
        result, _ = scan(lines)
        assert result.is_valid_sequence is False

    def test_three_level_valid(self):
        lines = _make_lines(
            "# 1 A", "## 1.1 B", "### 1.1.1 C",
            "### 1.1.2 D", "## 1.2 E", "# 2 F"
        )
        result, _ = scan(lines)
        assert result.is_valid_sequence is True


# ─── Info Warning ────────────────────────────────────────────────────────────


class TestInfoWarning:

    def test_warning_on_invalid_sequence_with_numbers(self):
        """Invalid sequence with suspected numbers → Info warning."""
        lines = _make_lines("# 1.0 概述", "## 2.0 Release", "## 3.1 日志")
        _, warnings = scan(lines)
        assert len(warnings) == 1
        assert "not a valid numbering sequence" in warnings[0].message
        assert "--force-strip" in warnings[0].message

    def test_no_warning_on_valid_sequence(self):
        lines = _make_lines("# 1 A", "# 2 B", "# 3 C")
        _, warnings = scan(lines)
        assert warnings == []

    def test_no_warning_when_no_numbers(self):
        lines = _make_lines("# A", "## B")
        _, warnings = scan(lines)
        assert warnings == []

    def test_no_warning_on_empty_document(self):
        lines = _make_lines("")
        _, warnings = scan(lines)
        assert warnings == []

    def test_warning_message_format(self):
        """Warning message matches SPEC format."""
        lines = _make_lines("# 1.0 A", "# 2.0 B")
        _, warnings = scan(lines)
        expected = (
            "number prefixes detected but not a valid numbering sequence, "
            "skipping strip. Use --force-strip to override."
        )
        assert warnings[0].message == expected


# ─── Fixture 文件集成测试 ────────────────────────────────────────────────────


class TestFixtureBasic:

    def test_basic_fixture(self):
        content = (FIXTURES / "basic.md").read_text(encoding="utf-8")
        lines = preprocess(content)
        result, warnings = scan(lines)
        assert len(result.headings) == 6
        levels = [h.level for h in result.headings]
        assert levels == [1, 2, 3, 3, 2, 1]
        assert result.min_level == 1
        assert result.is_valid_sequence is False  # no numbering
        assert warnings == []


class TestFixtureWithExistingNumbers:

    def test_existing_numbers_fixture(self):
        content = (FIXTURES / "with_existing_numbers.md").read_text(encoding="utf-8")
        lines = preprocess(content)
        result, warnings = scan(lines)
        assert len(result.headings) == 6
        assert result.headings[0].suspected_number == "1"
        assert result.headings[1].suspected_number == "1.1"
        assert result.headings[2].suspected_number == "1.1.1"
        assert result.headings[3].suspected_number == "1.1.2"
        assert result.headings[4].suspected_number == "1.2"
        assert result.headings[5].suspected_number == "2"
        assert result.is_valid_sequence is True
        assert warnings == []


class TestFixtureVersionTitles:

    def test_version_titles_fixture(self):
        content = (FIXTURES / "version_titles.md").read_text(encoding="utf-8")
        lines = preprocess(content)
        result, warnings = scan(lines)
        # Version numbers are extracted as suspected but sequence is invalid
        assert result.is_valid_sequence is False
        # Should have a warning about invalid sequence
        assert len(warnings) == 1
        assert "not a valid numbering sequence" in warnings[0].message
        # Titles like "3D 建模规范" and "5G 技术白皮书" should NOT have suspected numbers
        titles_without_numbers = [
            h for h in result.headings if h.suspected_number is None
        ]
        title_texts = [h.title_text for h in titles_without_numbers]
        assert any("3D" in t for t in title_texts)
        assert any("5G" in t for t in title_texts)


class TestFixtureEmptyHeadings:

    def test_empty_headings_fixture(self):
        content = (FIXTURES / "empty_headings.md").read_text(encoding="utf-8")
        lines = preprocess(content)
        result, _ = scan(lines)
        # Only non-empty headings should be identified
        titles = [h.title_text for h in result.headings]
        assert "正常标题" in titles
        assert "另一个正常标题" in titles
        # Empty headings (# , ##  ) should NOT be in the list
        assert len(result.headings) == 2
