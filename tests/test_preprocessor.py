"""Tests for preprocessor.py — newline normalization, line splitting, protected regions."""

from feishu2md.preprocessor import preprocess


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
