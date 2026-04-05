"""Tests for preprocessor.py — newline normalization, line splitting, protected regions."""

from pathlib import Path

from feishu2md.preprocessor import preprocess

FIXTURES = Path(__file__).resolve().parent / "fixtures"


# ─── 换行符统一 ──────────────────────────────────────────────────────────────


class TestNewlineNormalization:

    def test_crlf_to_lf(self):
        lines = preprocess("a\r\nb\r\nc")
        texts = [l.raw_text for l in lines]
        assert texts == ["a", "b", "c"]

    def test_lf_preserved(self):
        lines = preprocess("a\nb\nc")
        texts = [l.raw_text for l in lines]
        assert texts == ["a", "b", "c"]

    def test_mixed_newlines(self):
        lines = preprocess("a\r\nb\nc\r\n")
        texts = [l.raw_text for l in lines]
        assert texts == ["a", "b", "c", ""]


# ─── 行分割与 LineInfo 创建 ──────────────────────────────────────────────────


class TestLineSplitting:

    def test_line_numbers_1_based(self):
        lines = preprocess("a\nb\nc")
        assert [l.line_number for l in lines] == [1, 2, 3]

    def test_empty_content(self):
        lines = preprocess("")
        assert len(lines) == 1
        assert lines[0].raw_text == ""
        assert lines[0].line_number == 1

    def test_single_line_no_newline(self):
        lines = preprocess("hello")
        assert len(lines) == 1
        assert lines[0].raw_text == "hello"

    def test_trailing_newline(self):
        lines = preprocess("a\nb\n")
        assert len(lines) == 3
        assert lines[2].raw_text == ""

    def test_defaults_not_protected(self):
        lines = preprocess("# hello\nworld")
        for l in lines:
            assert l.is_protected is False
            assert l.is_blockquote is False
            assert l.heading_level is None
            assert l.heading_text is None


# ─── 代码块保护 ──────────────────────────────────────────────────────────────


class TestCodeBlockProtection:

    def test_basic_code_block(self):
        content = "before\n```\ncode line\n```\nafter"
        lines = preprocess(content)
        assert lines[0].is_protected is False   # before
        assert lines[1].is_protected is True    # ```
        assert lines[2].is_protected is True    # code line
        assert lines[3].is_protected is True    # ```
        assert lines[4].is_protected is False   # after

    def test_code_block_with_language(self):
        content = "```python\n# not a heading\n```"
        lines = preprocess(content)
        assert lines[0].is_protected is True
        assert lines[1].is_protected is True
        assert lines[2].is_protected is True

    def test_multi_backtick_code_block(self):
        content = "`````\n```\nstill inside\n`````"
        lines = preprocess(content)
        assert lines[0].is_protected is True    # `````
        assert lines[1].is_protected is True    # ``` (not closing, fewer backticks)
        assert lines[2].is_protected is True    # still inside
        assert lines[3].is_protected is True    # ````` (closing)

    def test_tilde_code_block(self):
        content = "~~~\ncode\n~~~"
        lines = preprocess(content)
        assert lines[0].is_protected is True
        assert lines[1].is_protected is True
        assert lines[2].is_protected is True

    def test_mismatched_fence_not_closing(self):
        """~~~ cannot close a ``` block."""
        content = "```\ncode\n~~~\nmore code\n```"
        lines = preprocess(content)
        assert lines[2].is_protected is True    # ~~~ inside ``` block
        assert lines[3].is_protected is True    # more code
        assert lines[4].is_protected is True    # ``` closing

    def test_fewer_backticks_not_closing(self):
        """Closing fence must have >= opening backtick count."""
        content = "````\ncode\n```\nstill code\n````"
        lines = preprocess(content)
        assert lines[2].is_protected is True    # ``` (not closing, fewer)
        assert lines[3].is_protected is True    # still code
        assert lines[4].is_protected is True    # ```` (closing)

    def test_unclosed_code_block(self):
        """Unclosed code block protects everything after it."""
        content = "before\n```\ncode\nmore code"
        lines = preprocess(content)
        assert lines[0].is_protected is False
        assert lines[1].is_protected is True
        assert lines[2].is_protected is True
        assert lines[3].is_protected is True

    def test_closing_fence_with_trailing_spaces(self):
        content = "```\ncode\n```   "
        lines = preprocess(content)
        assert lines[0].is_protected is True
        assert lines[1].is_protected is True
        assert lines[2].is_protected is True
        # After closing, subsequent lines should not be protected
        # (no subsequent lines in this case)

    def test_closing_fence_must_be_only_fence(self):
        """Closing fence line must have only the fence chars + optional whitespace."""
        content = "```\ncode\n``` some text\nstill inside\n```"
        lines = preprocess(content)
        assert lines[2].is_protected is True   # ``` some text — not a close
        assert lines[3].is_protected is True   # still inside
        assert lines[4].is_protected is True   # ``` — close

    def test_consecutive_code_blocks(self):
        """After closing one code block, a new one can start immediately."""
        content = "```\nfirst\n```\n```\nsecond\n```\nafter"
        lines = preprocess(content)
        assert lines[0].is_protected is True    # ``` open 1
        assert lines[1].is_protected is True    # first
        assert lines[2].is_protected is True    # ``` close 1
        assert lines[3].is_protected is True    # ``` open 2
        assert lines[4].is_protected is True    # second
        assert lines[5].is_protected is True    # ``` close 2
        assert lines[6].is_protected is False   # after


# ─── HTML 注释保护 ────────────────────────────────────────────────────────────


class TestHtmlCommentProtection:

    def test_single_line_comment(self):
        content = "before\n<!-- comment -->\nafter"
        lines = preprocess(content)
        assert lines[0].is_protected is False
        assert lines[1].is_protected is True
        assert lines[2].is_protected is False

    def test_multiline_comment(self):
        content = "before\n<!-- start\nmiddle\nend -->\nafter"
        lines = preprocess(content)
        assert lines[0].is_protected is False
        assert lines[1].is_protected is True
        assert lines[2].is_protected is True
        assert lines[3].is_protected is True
        assert lines[4].is_protected is False

    def test_unclosed_comment(self):
        content = "before\n<!-- start\nrest of file"
        lines = preprocess(content)
        assert lines[0].is_protected is False
        assert lines[1].is_protected is True
        assert lines[2].is_protected is True

    def test_comment_with_heading_inside(self):
        content = "<!-- \n# not a heading\n-->"
        lines = preprocess(content)
        assert lines[1].is_protected is True


# ─── Front matter 保护 ───────────────────────────────────────────────────────


class TestFrontMatterProtection:

    def test_basic_front_matter(self):
        content = "---\ntitle: hello\ndate: 2024\n---\n# Heading"
        lines = preprocess(content)
        assert lines[0].is_protected is True    # ---
        assert lines[1].is_protected is True    # title
        assert lines[2].is_protected is True    # date
        assert lines[3].is_protected is True    # ---
        assert lines[4].is_protected is False   # # Heading

    def test_front_matter_with_trailing_spaces(self):
        content = "---\ntitle: hi\n---   \nafter"
        lines = preprocess(content)
        assert lines[0].is_protected is True
        assert lines[1].is_protected is True
        assert lines[2].is_protected is True    # ---   (matches ^---\s*$)
        assert lines[3].is_protected is False

    def test_not_front_matter_if_not_first_line(self):
        """--- not at file start is not front matter, but may be Setext H2."""
        content = "hello\n---\ntitle: hi\n---"
        lines = preprocess(content)
        # --- after "hello" → Setext H2 → "## hello"
        # --- after "title: hi" → Setext H2 → "## title: hi"
        # Both underlines removed, 4 lines → 2 lines
        assert len(lines) == 2
        assert lines[0].raw_text == "## hello"
        assert lines[0].is_protected is False
        assert lines[1].raw_text == "## title: hi"
        assert lines[1].is_protected is False

    def test_front_matter_first_close_wins(self):
        """Only the first matching --- closes the front matter."""
        content = "---\nkey: value\n---\n---\nafter"
        lines = preprocess(content)
        assert lines[0].is_protected is True    # --- open
        assert lines[1].is_protected is True    # key: value
        assert lines[2].is_protected is True    # --- close
        assert lines[3].is_protected is False   # --- (not front matter)
        assert lines[4].is_protected is False   # after

    def test_unclosed_front_matter(self):
        """If no closing --- found, entire file is front matter."""
        content = "---\ntitle: hi\nno close"
        lines = preprocess(content)
        assert lines[0].is_protected is True
        assert lines[1].is_protected is True
        assert lines[2].is_protected is True

    def test_empty_front_matter(self):
        content = "---\n---\n# Heading"
        lines = preprocess(content)
        assert lines[0].is_protected is True
        assert lines[1].is_protected is True
        assert lines[2].is_protected is False

    def test_four_dashes_does_not_close(self):
        """---- (4 dashes) does NOT match ^---\\s*$ — must be exactly 3."""
        content = "---\ntitle: hi\n----\nstill fm\n---\nafter"
        lines = preprocess(content)
        assert lines[2].is_protected is True    # ---- is NOT a close
        assert lines[3].is_protected is True    # still inside
        assert lines[4].is_protected is True    # --- closes
        assert lines[5].is_protected is False   # after


# ─── Blockquote 标记 ─────────────────────────────────────────────────────────


class TestBlockquoteMarking:

    def test_basic_blockquote(self):
        content = "> quoted text\nnormal text"
        lines = preprocess(content)
        assert lines[0].is_blockquote is True
        assert lines[1].is_blockquote is False

    def test_blockquote_with_heading(self):
        content = "> # Heading inside quote"
        lines = preprocess(content)
        assert lines[0].is_blockquote is True
        assert lines[0].is_protected is False  # blockquote is NOT protected

    def test_nested_blockquote(self):
        content = ">> deeply nested"
        lines = preprocess(content)
        assert lines[0].is_blockquote is True

    def test_blockquote_empty(self):
        content = ">"
        lines = preprocess(content)
        assert lines[0].is_blockquote is True

    def test_blockquote_not_in_code_block(self):
        """Inside code block, > should not be marked as blockquote."""
        content = "```\n> not a quote\n```"
        lines = preprocess(content)
        assert lines[1].is_blockquote is False
        assert lines[1].is_protected is True


# ─── 受保护区域优先级 ────────────────────────────────────────────────────────


class TestProtectionPriority:

    def test_code_block_inside_html_comment_impossible(self):
        """Once in HTML comment, code fence markers are ignored."""
        content = "<!--\n```\n# not heading\n```\n-->\nafter"
        lines = preprocess(content)
        # All inside comment are protected
        assert lines[1].is_protected is True
        assert lines[2].is_protected is True
        assert lines[3].is_protected is True
        assert lines[4].is_protected is True
        assert lines[5].is_protected is False

    def test_html_comment_inside_code_block_ignored(self):
        """Inside code block, <!-- is not an HTML comment opener."""
        content = "```\n<!-- not a comment\n-->\n```\nafter"
        lines = preprocess(content)
        assert lines[1].is_protected is True    # code block, not HTML comment
        assert lines[2].is_protected is True
        assert lines[3].is_protected is True    # ``` closing
        assert lines[4].is_protected is False

    def test_front_matter_then_code_block(self):
        content = "---\ntitle: hi\n---\n```\ncode\n```"
        lines = preprocess(content)
        assert lines[0].is_protected is True    # fm open
        assert lines[2].is_protected is True    # fm close
        assert lines[3].is_protected is True    # code fence
        assert lines[4].is_protected is True    # code
        assert lines[5].is_protected is True    # code fence close


# ─── Setext → ATX 标题转换 ───────────────────────────────────────────────────


class TestSetextToAtx:

    def test_equals_to_h1(self):
        content = "Title\n==="
        lines = preprocess(content)
        assert len(lines) == 1
        assert lines[0].raw_text == "# Title"

    def test_dashes_to_h2(self):
        content = "Title\n---"
        lines = preprocess(content)
        assert len(lines) == 1
        assert lines[0].raw_text == "## Title"

    def test_long_equals(self):
        content = "Title\n=========="
        lines = preprocess(content)
        assert len(lines) == 1
        assert lines[0].raw_text == "# Title"

    def test_long_dashes(self):
        content = "Title\n----------"
        lines = preprocess(content)
        assert len(lines) == 1
        assert lines[0].raw_text == "## Title"

    def test_equals_with_trailing_spaces(self):
        content = "Title\n===   "
        lines = preprocess(content)
        assert len(lines) == 1
        assert lines[0].raw_text == "# Title"

    def test_line_count_reduced(self):
        """Underline line is deleted, reducing total line count."""
        content = "before\nTitle\n===\nafter"
        lines = preprocess(content)
        assert len(lines) == 3  # before, # Title, after
        texts = [l.raw_text for l in lines]
        assert texts == ["before", "# Title", "after"]

    def test_original_line_number_preserved(self):
        """line_number stays as original, not re-numbered."""
        content = "before\nTitle\n===\nafter"
        lines = preprocess(content)
        assert lines[0].line_number == 1    # before
        assert lines[1].line_number == 2    # Title (originally line 2)
        assert lines[2].line_number == 4    # after (originally line 4)

    def test_empty_line_before_dashes_is_hr(self):
        """--- preceded by empty line is a horizontal rule, not Setext."""
        content = "text\n\n---\nafter"
        lines = preprocess(content)
        # No conversion — all 4 lines remain
        assert len(lines) == 4
        assert lines[2].raw_text == "---"

    def test_first_line_dashes_is_not_setext(self):
        """--- as the very first line with nothing before it — not Setext."""
        # Can't be Setext because there's no preceding text line.
        # (First line is --- which would be front matter open, but no close,
        #  so entire file is front matter / protected.)
        content = "---\ntext"
        lines = preprocess(content)
        # Front matter opens but never closes — both lines protected
        assert lines[0].is_protected is True
        assert lines[1].is_protected is True

    def test_not_converted_inside_code_block(self):
        content = "```\nTitle\n===\n```"
        lines = preprocess(content)
        assert len(lines) == 4  # no conversion
        assert lines[1].raw_text == "Title"
        assert lines[2].raw_text == "==="

    def test_not_converted_inside_html_comment(self):
        content = "<!--\nTitle\n===\n-->"
        lines = preprocess(content)
        assert len(lines) == 4
        assert lines[1].raw_text == "Title"

    def test_not_converted_in_front_matter(self):
        content = "---\nTitle\n===\n---"
        lines = preprocess(content)
        # All protected as front matter (=== doesn't match --- close)
        assert lines[2].raw_text == "==="
        assert lines[2].is_protected is True

    def test_not_converted_in_blockquote(self):
        content = "> Title\n> ==="
        lines = preprocess(content)
        assert len(lines) == 2
        assert lines[0].raw_text == "> Title"

    def test_multiple_setext_headings(self):
        content = "First\n===\ntext\nSecond\n---\nmore"
        lines = preprocess(content)
        assert len(lines) == 4  # 6 original - 2 underlines
        texts = [l.raw_text for l in lines]
        assert texts == ["# First", "text", "## Second", "more"]

    def test_two_dashes_too_short(self):
        """-- (only 2) is not a valid Setext underline (need >= 3)."""
        content = "Title\n--"
        lines = preprocess(content)
        assert len(lines) == 2  # no conversion
        assert lines[0].raw_text == "Title"
        assert lines[1].raw_text == "--"

    def test_two_equals_too_short(self):
        content = "Title\n=="
        lines = preprocess(content)
        assert len(lines) == 2
        assert lines[0].raw_text == "Title"

    def test_mixed_chars_not_setext(self):
        """=-= is not a valid Setext underline."""
        content = "Title\n=-="
        lines = preprocess(content)
        assert len(lines) == 2
        assert lines[0].raw_text == "Title"

    def test_hr_with_stars(self):
        """*** is a horizontal rule, never Setext (only = and - are)."""
        content = "text\n***"
        lines = preprocess(content)
        assert len(lines) == 2
        assert lines[0].raw_text == "text"
        assert lines[1].raw_text == "***"

    def test_consecutive_setext_headings(self):
        """Two Setext headings back-to-back."""
        content = "A\n===\nB\n==="
        lines = preprocess(content)
        assert len(lines) == 2
        assert lines[0].raw_text == "# A"
        assert lines[1].raw_text == "# B"

    def test_equals_as_first_line(self):
        """=== as the very first line — no preceding text, not Setext."""
        content = "===\ntext"
        lines = preprocess(content)
        assert len(lines) == 2
        assert lines[0].raw_text == "==="


# ─── Fixture 文件集成测试 ────────────────────────────────────────────────────


class TestFixtureCodeBlocks:

    def test_code_blocks_fixture(self):
        content = (FIXTURES / "code_blocks.md").read_text(encoding="utf-8")
        lines = preprocess(content)
        texts = [l.raw_text for l in lines]
        # # 代码示例 is a real heading (not protected)
        assert any("# 代码示例" in t for t in texts)
        # Lines inside ``` blocks are protected
        protected_texts = [l.raw_text for l in lines if l.is_protected]
        assert any("# 这不是标题" in t for t in protected_texts)
        assert any("# 多重反引号内的内容" in t for t in protected_texts)
        assert any("# 波浪号代码块" in t for t in protected_texts)
        # ## 第二节 is not protected
        non_protected = [l for l in lines if not l.is_protected]
        assert any("## 第二节" in l.raw_text for l in non_protected)


class TestFixtureSetextHeadings:

    def test_setext_fixture(self):
        content = (FIXTURES / "setext_headings.md").read_text(encoding="utf-8")
        lines = preprocess(content)
        texts = [l.raw_text for l in lines]
        # 产品概述 converted to # 产品概述
        assert "# 产品概述" in texts
        # 功能设计 converted to ## 功能设计
        assert "## 功能设计" in texts
        # 技术方案 converted to ## 技术方案
        assert "## 技术方案" in texts
        # --- (standalone) is NOT converted — remains as ---
        assert "---" in texts
        # 短下划线不转换 stays unconverted (-- is only 2 chars)
        assert "短下划线不转换" in texts
        assert "--" in texts


class TestFixtureFrontMatter:

    def test_front_matter_fixture(self):
        content = (FIXTURES / "front_matter.md").read_text(encoding="utf-8")
        lines = preprocess(content)
        # First 7 lines (--- through ---) are protected
        fm_lines = [l for l in lines if l.is_protected]
        assert any("title: 测试文档" in l.raw_text for l in fm_lines)
        assert any("date: 2024-01-01" in l.raw_text for l in fm_lines)
        # # 正文开始 is NOT protected
        non_protected = [l for l in lines if not l.is_protected]
        assert any("# 正文开始" in l.raw_text for l in non_protected)


class TestFixtureBlockquote:

    def test_blockquote_fixture(self):
        content = (FIXTURES / "blockquote.md").read_text(encoding="utf-8")
        lines = preprocess(content)
        # > lines are blockquote
        bq_lines = [l for l in lines if l.is_blockquote]
        assert len(bq_lines) >= 4
        assert any("# 引用里的标题" in l.raw_text for l in bq_lines)
        # Normal headings are NOT blockquote
        normal = [l for l in lines if not l.is_blockquote and not l.is_protected]
        assert any("# 正常标题" in l.raw_text for l in normal)
        assert any("## 正常的二级标题" in l.raw_text for l in normal)
        assert any("### 正常的三级标题" in l.raw_text for l in normal)


# --- Feishu bold heading conversion ---


class TestFeishuBoldHeadings:

    def test_top_level_escaped_dot(self):
        """'1\\. **Title**' -> '# Title'"""
        lines = preprocess("1\\. **Title**")
        assert lines[0].raw_text == "# Title"

    def test_top_level_number_2(self):
        lines = preprocess("2\\. **Second**")
        assert lines[0].raw_text == "# Second"

    def test_sub_level_2_segments(self):
        """'2.1 **Sub**' -> '## Sub'"""
        lines = preprocess("2.1 **Sub**")
        assert lines[0].raw_text == "## Sub"

    def test_sub_level_3_segments(self):
        """'3.1.1 **Deep**' -> '### Deep'"""
        lines = preprocess("3.1.1 **Deep**")
        assert lines[0].raw_text == "### Deep"

    def test_level_determined_by_segments(self):
        """Number of dot-separated segments = heading level."""
        lines = preprocess("1\\. **L1**\n2.1 **L2**\n3.1.1 **L3**")
        assert lines[0].raw_text == "# L1"
        assert lines[1].raw_text == "## L2"
        assert lines[2].raw_text == "### L3"

    def test_bold_markers_stripped(self):
        """** markers are removed from the heading text."""
        lines = preprocess("1\\. **Title**")
        assert "**" not in lines[0].raw_text

    def test_numbering_stripped(self):
        """Original numbering is removed (will be re-generated by numbering module)."""
        lines = preprocess("3.1.1 **Background**")
        assert "3.1.1" not in lines[0].raw_text
        assert lines[0].raw_text == "### Background"

    def test_not_converted_inside_code_block(self):
        content = "```\n1\\. **Not heading**\n```"
        lines = preprocess(content)
        protected = [l for l in lines if l.is_protected]
        assert any("1\\. **Not heading**" in l.raw_text for l in protected)

    def test_normal_bold_not_converted(self):
        """Regular bold text without number prefix is NOT converted."""
        lines = preprocess("**Just bold text**")
        assert lines[0].raw_text == "**Just bold text**"

    def test_normal_numbered_list_not_converted(self):
        """'1. Normal item' without bold is NOT converted."""
        lines = preprocess("1. Normal list item")
        assert lines[0].raw_text == "1. Normal list item"

    def test_partial_bold_not_converted(self):
        """'1\\. **Bold** and more text' is NOT converted (text after **)."""
        lines = preprocess("1\\. **Bold** and more text")
        assert lines[0].raw_text == "1\\. **Bold** and more text"

    def test_mixed_with_regular_headings(self):
        """Feishu bold headings coexist with regular ATX headings."""
        content = "# Real Heading\n\n1\\. **Feishu H1**\n\n2.1 **Feishu H2**"
        lines = preprocess(content)
        texts = [l.raw_text for l in lines]
        assert "# Real Heading" in texts
        # No doc title before numbered headings, so no level offset
        assert "# Feishu H1" in texts
        assert "## Feishu H2" in texts

    def test_doc_title_not_numbered(self):
        """Document title (bold line before numbered headings) stays as bold, not ATX."""
        content = "**Doc Title**\n\n1\\. **Section**\n\n2.1 **Sub**"
        lines = preprocess(content)
        texts = [l.raw_text for l in lines]
        # Title stays as bold (not converted to #)
        assert "**Doc Title**" in texts
        # Numbered headings shift down one level (title occupies H1 conceptually)
        assert "## Section" in texts   # 1-segment + offset=1 → H2
        assert "### Sub" in texts      # 2-segment + offset=1 → H3

    def test_no_title_no_offset(self):
        """Without a doc title, numbered headings use their natural level."""
        content = "1\\. **Section**\n\n2.1 **Sub**"
        lines = preprocess(content)
        texts = [l.raw_text for l in lines]
        assert "# Section" in texts   # 1-segment → H1
        assert "## Sub" in texts      # 2-segment → H2
