"""Tests for idempotency — running the tool twice produces identical output."""

from pathlib import Path

from feishu2md.preprocessor import preprocess
from feishu2md.scanner import scan
from feishu2md.stripper import strip
from feishu2md.numbering import generate

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _run_pipeline(content: str, max_level: int = 3, strip_mode: str = "auto") -> str:
    """Run the full pipeline on content and return output text."""
    lines = preprocess(content)
    sr, _ = scan(lines)
    lines, sr, _ = strip(lines, sr, mode=strip_mode)
    if strip_mode != "strip_only":
        lines, _ = generate(lines, sr, max_level=max_level)
    return "\n".join(line.raw_text for line in lines)


class TestBasicIdempotency:

    def test_basic_two_passes_identical(self):
        content = "# A\n\n## B\n\n### C\n"
        pass1 = _run_pipeline(content)
        pass2 = _run_pipeline(pass1)
        assert pass1 == pass2

    def test_full_spec_example(self):
        content = (FIXTURES / "basic.md").read_text(encoding="utf-8")
        pass1 = _run_pipeline(content)
        pass2 = _run_pipeline(pass1)
        assert pass1 == pass2

    def test_existing_numbers_idempotent(self):
        content = (FIXTURES / "with_existing_numbers.md").read_text(encoding="utf-8")
        pass1 = _run_pipeline(content)
        pass2 = _run_pipeline(pass1)
        assert pass1 == pass2

    def test_three_passes_identical(self):
        content = "# X\n## Y\n### Z\n"
        pass1 = _run_pipeline(content)
        pass2 = _run_pipeline(pass1)
        pass3 = _run_pipeline(pass2)
        assert pass1 == pass2 == pass3


class TestModifiedStructure:

    def test_add_heading_then_rerun(self):
        """After numbering, add a heading and rerun — numbers update correctly."""
        original = "# A\n## B\n"
        pass1 = _run_pipeline(original)
        # Insert a new heading between existing ones
        modified = pass1.replace("## 1.1 B", "## 1.1 B\n## New Section")
        pass2 = _run_pipeline(modified)
        assert "## 1.1 B" in pass2
        assert "## 1.2 New Section" in pass2


class TestMaxLevelIdempotency:

    def test_max_level_2(self):
        content = "# A\n## B\n### C\n"
        pass1 = _run_pipeline(content, max_level=2)
        pass2 = _run_pipeline(pass1, max_level=2)
        assert pass1 == pass2

    def test_max_level_1(self):
        """max-level=1: only H1 gets numbered, idempotent with auto mode."""
        content = "# A\n## B\n### C\n"
        pass1 = _run_pipeline(content, max_level=1)
        pass2 = _run_pipeline(pass1, max_level=1)
        assert pass1 == pass2

    def test_max_level_1_all_h1(self):
        """When all headings are H1, max-level=1 is idempotent."""
        content = "# A\n# B\n# C\n"
        pass1 = _run_pipeline(content, max_level=1)
        pass2 = _run_pipeline(pass1, max_level=1)
        assert pass1 == pass2

    def test_max_level_1_multiple_h1(self):
        """Multiple H1 with sub-headings, max-level=1."""
        content = "# A\n## B\n# C\n## D\n### E\n"
        pass1 = _run_pipeline(content, max_level=1)
        pass2 = _run_pipeline(pass1, max_level=1)
        assert pass1 == pass2


class TestBlockquoteIdempotency:

    def test_blockquote_preserved(self):
        content = (FIXTURES / "blockquote.md").read_text(encoding="utf-8")
        pass1 = _run_pipeline(content)
        pass2 = _run_pipeline(pass1)
        assert pass1 == pass2

    def test_blockquote_headings_untouched(self):
        content = "# A\n\n> # Quoted\n\n## B\n"
        pass1 = _run_pipeline(content)
        pass2 = _run_pipeline(pass1)
        assert pass1 == pass2
        assert "> # Quoted" in pass1


class TestFormattedHeadingsIdempotency:

    def test_bold_heading(self):
        content = "# **Bold Title**\n## Normal\n"
        pass1 = _run_pipeline(content)
        pass2 = _run_pipeline(pass1)
        assert pass1 == pass2
        assert "**Bold Title**" in pass1

    def test_link_heading(self):
        content = "# [Link](url)\n## Other\n"
        pass1 = _run_pipeline(content)
        pass2 = _run_pipeline(pass1)
        assert pass1 == pass2

    def test_inline_code_heading(self):
        content = "# `code` title\n## Other\n"
        pass1 = _run_pipeline(content)
        pass2 = _run_pipeline(pass1)
        assert pass1 == pass2

    def test_formatted_fixture(self):
        content = (FIXTURES / "formatted_headings.md").read_text(encoding="utf-8")
        pass1 = _run_pipeline(content)
        pass2 = _run_pipeline(pass1)
        assert pass1 == pass2
