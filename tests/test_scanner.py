"""Tests for scanner.py — heading identification, metadata population, HeadingInfo creation."""

from feishu2md.models import LineInfo, ScanResult
from feishu2md.scanner import scan


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

    def test_suspected_number_is_none_for_now(self):
        """suspected_number is None until numbering extraction is implemented."""
        lines = _make_lines("# 1 Title", "## 1.1 Sub")
        result, _ = scan(lines)
        for h in result.headings:
            assert h.suspected_number is None

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

    def test_warnings_empty_for_now(self):
        """No warnings generated yet (sequence validation not implemented)."""
        lines = _make_lines("# A", "## B")
        _, warnings = scan(lines)
        assert warnings == []

    def test_is_valid_sequence_false_for_now(self):
        """Sequence validation not yet implemented — always False."""
        lines = _make_lines("# 1 A", "## 1.1 B")
        result, _ = scan(lines)
        assert result.is_valid_sequence is False
