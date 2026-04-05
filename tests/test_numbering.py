"""Tests for numbering.py — counter logic, level jump, max-level, prefix concatenation."""

from pathlib import Path

from feishu2md.models import HeadingInfo, LineInfo, ScanResult
from feishu2md.numbering import generate
from feishu2md.preprocessor import preprocess
from feishu2md.scanner import scan
from feishu2md.stripper import strip

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _heading_line(level: int, text: str, line_number: int = 1) -> LineInfo:
    prefix = "#" * level
    return LineInfo(
        line_number=line_number,
        raw_text=f"{prefix} {text}",
        heading_level=level,
        heading_text=text,
    )


def _scan_result(lines: list[LineInfo], min_level: int | None = None) -> ScanResult:
    headings = []
    auto_min = 6
    for i, line in enumerate(lines):
        if line.heading_level is not None:
            headings.append(HeadingInfo(
                line_index=i, level=line.heading_level,
                title_text=line.heading_text, suspected_number=None,
            ))
            if line.heading_level < auto_min:
                auto_min = line.heading_level
    if not headings:
        auto_min = 1
    return ScanResult(
        headings=headings,
        min_level=min_level if min_level is not None else auto_min,
        is_valid_sequence=False,
    )


# --- Basic counter logic ---


class TestBasicCounter:

    def test_single_h1(self):
        lines = [_heading_line(1, "Title")]
        sr = _scan_result(lines)
        generate(lines, sr, max_level=3)
        assert lines[0].heading_text == "1 Title"

    def test_three_levels(self):
        lines = [
            _heading_line(1, "A", 1),
            _heading_line(2, "B", 3),
            _heading_line(3, "C", 5),
        ]
        sr = _scan_result(lines)
        generate(lines, sr, max_level=3)
        assert lines[0].heading_text == "1 A"
        assert lines[1].heading_text == "1.1 B"
        assert lines[2].heading_text == "1.1.1 C"

    def test_same_level_increment(self):
        lines = [
            _heading_line(1, "X", 1),
            _heading_line(2, "A", 2),
            _heading_line(2, "B", 3),
            _heading_line(2, "C", 4),
        ]
        sr = _scan_result(lines)
        generate(lines, sr, max_level=3)
        assert lines[1].heading_text == "1.1 A"
        assert lines[2].heading_text == "1.2 B"
        assert lines[3].heading_text == "1.3 C"

    def test_cross_h1_reset(self):
        lines = [
            _heading_line(1, "A", 1),
            _heading_line(2, "B", 2),
            _heading_line(1, "C", 3),
            _heading_line(2, "D", 4),
        ]
        sr = _scan_result(lines)
        generate(lines, sr, max_level=3)
        assert lines[0].heading_text == "1 A"
        assert lines[1].heading_text == "1.1 B"
        assert lines[2].heading_text == "2 C"
        assert lines[3].heading_text == "2.1 D"

    def test_full_spec_example(self):
        """SPEC example: H1,H2,H3,H3,H2,H1 -> 1, 1.1, 1.1.1, 1.1.2, 1.2, 2."""
        lines = [
            _heading_line(1, "A", 1),
            _heading_line(2, "B", 3),
            _heading_line(3, "C", 5),
            _heading_line(3, "D", 7),
            _heading_line(2, "E", 9),
            _heading_line(1, "F", 11),
        ]
        sr = _scan_result(lines)
        generate(lines, sr, max_level=3)
        texts = [l.heading_text for l in lines]
        assert texts == ["1 A", "1.1 B", "1.1.1 C", "1.1.2 D", "1.2 E", "2 F"]


# --- min_level offset ---


class TestMinLevelOffset:

    def test_start_from_h2(self):
        lines = [
            _heading_line(2, "A", 1),
            _heading_line(3, "B", 3),
            _heading_line(3, "C", 5),
            _heading_line(2, "D", 7),
        ]
        sr = _scan_result(lines)
        generate(lines, sr, max_level=3)
        assert lines[0].heading_text == "1 A"
        assert lines[1].heading_text == "1.1 B"
        assert lines[2].heading_text == "1.2 C"
        assert lines[3].heading_text == "2 D"

    def test_start_from_h3(self):
        lines = [
            _heading_line(3, "A", 1),
            _heading_line(3, "B", 2),
        ]
        sr = _scan_result(lines)
        generate(lines, sr, max_level=3)
        assert lines[0].heading_text == "1 A"
        assert lines[1].heading_text == "2 B"


# --- Level jump ---


class TestLevelJump:

    def test_h1_to_h3_fills_h2(self):
        lines = [
            _heading_line(1, "A", 1),
            _heading_line(3, "B", 3),
        ]
        sr = _scan_result(lines)
        generate(lines, sr, max_level=3)
        assert lines[0].heading_text == "1 A"
        assert lines[1].heading_text == "1.1.1 B"

    def test_jump_generates_warning(self):
        lines = [
            _heading_line(1, "A", 1),
            _heading_line(3, "B", 5),
        ]
        sr = _scan_result(lines)
        _, warnings = generate(lines, sr, max_level=3)
        assert len(warnings) == 1
        assert "jumped from H1 to H3" in warnings[0].message
        assert "line 5" in warnings[0].message
        assert "auto-filled H2" in warnings[0].message

    def test_warning_line_number(self):
        lines = [
            _heading_line(1, "A", 10),
            _heading_line(3, "B", 42),
        ]
        sr = _scan_result(lines)
        _, warnings = generate(lines, sr, max_level=3)
        assert warnings[0].line_number == 42

    def test_warning_message_exact_format(self):
        """Verify warning message matches SPEC format exactly."""
        lines = [
            _heading_line(1, "A", 1),
            _heading_line(3, "B", 42),
        ]
        sr = _scan_result(lines)
        _, warnings = generate(lines, sr, max_level=3)
        expected = "heading level jumped from H1 to H3 at line 42, auto-filled H2 counter"
        assert warnings[0].message == expected

    def test_no_warning_without_jump(self):
        lines = [
            _heading_line(1, "A", 1),
            _heading_line(2, "B", 2),
            _heading_line(3, "C", 3),
        ]
        sr = _scan_result(lines)
        _, warnings = generate(lines, sr, max_level=3)
        assert warnings == []

    def test_jump_from_h2_start(self):
        """Document starts at H2, jumps to H4 (skipping H3)."""
        lines = [
            _heading_line(2, "A", 1),
            _heading_line(4, "B", 3),
        ]
        sr = _scan_result(lines)
        generate(lines, sr, max_level=3)
        assert lines[0].heading_text == "1 A"
        assert lines[1].heading_text == "1.1.1 B"


# --- max-level ---


class TestMaxLevel:

    def test_max_level_2_skips_h3(self):
        lines = [
            _heading_line(1, "A", 1),
            _heading_line(2, "B", 2),
            _heading_line(3, "C", 3),
        ]
        sr = _scan_result(lines)
        generate(lines, sr, max_level=2)
        assert lines[0].heading_text == "1 A"
        assert lines[1].heading_text == "1.1 B"
        assert lines[2].heading_text == "C"  # NOT numbered

    def test_max_level_1_only_h1(self):
        lines = [
            _heading_line(1, "A", 1),
            _heading_line(2, "B", 2),
            _heading_line(3, "C", 3),
        ]
        sr = _scan_result(lines)
        generate(lines, sr, max_level=1)
        assert lines[0].heading_text == "1 A"
        assert lines[1].heading_text == "B"
        assert lines[2].heading_text == "C"

    def test_max_level_does_not_affect_raw_text_of_skipped(self):
        lines = [
            _heading_line(1, "A", 1),
            _heading_line(3, "C", 3),
        ]
        sr = _scan_result(lines)
        generate(lines, sr, max_level=1)
        assert lines[1].raw_text == "### C"  # unchanged


# --- Prefix concatenation ---


class TestPrefixConcatenation:

    def test_heading_text_updated(self):
        lines = [_heading_line(1, "Title")]
        sr = _scan_result(lines)
        generate(lines, sr, max_level=3)
        assert lines[0].heading_text == "1 Title"

    def test_raw_text_updated(self):
        lines = [_heading_line(2, "Title")]
        sr = _scan_result(lines, min_level=2)
        generate(lines, sr, max_level=3)
        assert lines[0].raw_text == "## 1 Title"

    def test_markdown_format_preserved(self):
        lines = [
            _heading_line(1, "X", 1),
            _heading_line(2, "**Bold**", 2),
        ]
        sr = _scan_result(lines)
        generate(lines, sr, max_level=3)
        assert lines[1].heading_text == "1.1 **Bold**"
        assert lines[1].raw_text == "## 1.1 **Bold**"

    def test_non_heading_lines_untouched(self):
        normal = LineInfo(line_number=1, raw_text="normal text")
        heading = _heading_line(1, "Title", 2)
        lines = [normal, heading]
        sr = _scan_result(lines)
        generate(lines, sr, max_level=3)
        assert lines[0].raw_text == "normal text"


# --- Return structure ---


class TestReturnStructure:

    def test_returns_tuple(self):
        lines = [_heading_line(1, "A")]
        sr = _scan_result(lines)
        result = generate(lines, sr, max_level=3)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_returns_same_lines(self):
        lines = [_heading_line(1, "A")]
        sr = _scan_result(lines)
        result_lines, _ = generate(lines, sr, max_level=3)
        assert result_lines is lines

    def test_warnings_is_list(self):
        lines = [_heading_line(1, "A")]
        sr = _scan_result(lines)
        _, warnings = generate(lines, sr, max_level=3)
        assert isinstance(warnings, list)

    def test_empty_document(self):
        lines = [LineInfo(line_number=1, raw_text="no headings")]
        sr = _scan_result(lines)
        _, warnings = generate(lines, sr, max_level=3)
        assert warnings == []


# --- Fixture integration tests ---


class TestFixtureLevelJump:

    def test_level_jump_fixture(self):
        """Full pipeline: preprocess -> scan -> strip -> generate on level_jump.md."""
        content = (FIXTURES / "level_jump.md").read_text(encoding="utf-8")
        lines = preprocess(content)
        sr, _ = scan(lines)
        lines, sr, _ = strip(lines, sr, "auto")
        lines, warnings = generate(lines, sr, max_level=3)

        numbered = [l for l in lines if l.heading_level is not None]
        texts = [l.heading_text for l in numbered]

        # H1 Overview -> 1 Overview
        assert texts[0] == "1 Overview"
        # H3 Detail Section -> 1.1.1 Detail Section (H2 auto-filled)
        assert texts[1] == "1.1.1 Detail Section"
        # Should have at least one warning about level jump
        assert len(warnings) >= 1
        assert any("jumped" in w.message for w in warnings)


class TestFixtureStartFromH2:

    def test_start_from_h2_fixture(self):
        """Full pipeline on start_from_h2.md — numbering starts from 1, not 0.1."""
        content = (FIXTURES / "start_from_h2.md").read_text(encoding="utf-8")
        lines = preprocess(content)
        sr, _ = scan(lines)
        lines, sr, _ = strip(lines, sr, "auto")
        lines, warnings = generate(lines, sr, max_level=3)

        numbered = [l for l in lines if l.heading_level is not None]
        texts = [l.heading_text for l in numbered]

        # H2 starts at 1, not 0.1
        assert texts[0] == "1 Feature Design"
        assert texts[1] == "1.1 Interaction Logic"
        assert texts[2] == "1.2 Visual Guidelines"
        assert texts[3] == "2 Technical Plan"
        assert texts[4] == "2.1 Architecture"
        assert texts[5] == "2.2 Database Design"
        # No warnings (no level jumps)
        assert warnings == []
