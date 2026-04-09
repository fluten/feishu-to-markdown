"""Tests for docx_patcher.py — currently focused on the Feishu detection gate.

Full unit test coverage for the rest of the module is tracked in todo_fix.md (T1).
"""

from feishu2md.docx_patcher import _is_feishu_docx


# 标准飞书空 styles.xml（121 字节，实测来自真实导出）
_FEISHU_EMPTY_STYLES = (
    b'<?xml version="1.0" encoding="UTF-8"?>'
    b'<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>'
)

# 标准 Word styles.xml 的最小样例（带至少一条 style 定义）
_REAL_WORD_STYLES = b"""<?xml version="1.0" encoding="UTF-8"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>
  <w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/></w:style>
  <w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/></w:style>
""" + b"  <w:style/>" * 50 + b"</w:styles>"  # 凑超过 300 字节


# 飞书风格 numbering.xml：abstractNumId 是大数字，每个 abstractNum 单 lvl
_FEISHU_NUMBERING = b"""<?xml version="1.0" encoding="UTF-8"?>
<w:numbering xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:abstractNum w:abstractNumId="656820"><w:lvl><w:start w:val="1"/><w:numFmt w:val="decimal"/><w:lvlText w:val="%1."/></w:lvl></w:abstractNum>
  <w:abstractNum w:abstractNumId="656821"><w:lvl><w:start w:val="1"/><w:numFmt w:val="lowerLetter"/><w:lvlText w:val="%1."/></w:lvl></w:abstractNum>
  <w:num w:numId="1"><w:abstractNumId w:val="656820"/></w:num>
  <w:num w:numId="2"><w:abstractNumId w:val="656821"/></w:num>
</w:numbering>"""

# 标准 Word numbering.xml：小 abstractNumId，多 lvl
_REAL_WORD_NUMBERING = b"""<?xml version="1.0" encoding="UTF-8"?>
<w:numbering xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:abstractNum w:abstractNumId="0">
    <w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="decimal"/><w:lvlText w:val="%1."/></w:lvl>
    <w:lvl w:ilvl="1"><w:start w:val="1"/><w:numFmt w:val="lowerLetter"/><w:lvlText w:val="%2."/></w:lvl>
    <w:lvl w:ilvl="2"><w:start w:val="1"/><w:numFmt w:val="lowerRoman"/><w:lvlText w:val="%3."/></w:lvl>
  </w:abstractNum>
  <w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num>
</w:numbering>"""


class TestIsFeishuDocx:
    """检测函数 _is_feishu_docx 的边界覆盖。"""

    def test_feishu_with_lists_and_large_abstract_id(self):
        """空 styles + 大 abstractNumId → 飞书。"""
        files = {
            "word/styles.xml": _FEISHU_EMPTY_STYLES,
            "word/numbering.xml": _FEISHU_NUMBERING,
        }
        assert _is_feishu_docx(files) is True

    def test_feishu_with_lists_and_single_lvl_only(self):
        """空 styles + 小 abstractNumId 但全部单 lvl → 飞书（指纹 2）。"""
        small_id_single_lvl = b"""<?xml version="1.0"?>
<w:numbering xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:abstractNum w:abstractNumId="1"><w:lvl><w:start w:val="1"/><w:numFmt w:val="decimal"/><w:lvlText w:val="%1."/></w:lvl></w:abstractNum>
  <w:abstractNum w:abstractNumId="2"><w:lvl><w:start w:val="2"/><w:numFmt w:val="decimal"/><w:lvlText w:val="%1."/></w:lvl></w:abstractNum>
  <w:num w:numId="1"><w:abstractNumId w:val="1"/></w:num>
</w:numbering>"""
        files = {
            "word/styles.xml": _FEISHU_EMPTY_STYLES,
            "word/numbering.xml": small_id_single_lvl,
        }
        assert _is_feishu_docx(files) is True

    def test_feishu_with_no_lists(self):
        """空 styles + 没有 numbering.xml → 飞书（仅有标题没有列表的飞书文档）。"""
        files = {"word/styles.xml": _FEISHU_EMPTY_STYLES}
        assert _is_feishu_docx(files) is True

    def test_feishu_with_empty_numbering(self):
        """空 styles + 空 numbering（没有 abstractNum 定义）→ 飞书。"""
        empty_numbering = (
            b'<?xml version="1.0"?>'
            b'<w:numbering xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>'
        )
        files = {
            "word/styles.xml": _FEISHU_EMPTY_STYLES,
            "word/numbering.xml": empty_numbering,
        }
        assert _is_feishu_docx(files) is True

    def test_real_word_doc_rejected(self):
        """完整 styles.xml → 不是飞书（必要条件失败）。"""
        files = {
            "word/styles.xml": _REAL_WORD_STYLES,
            "word/numbering.xml": _REAL_WORD_NUMBERING,
        }
        assert _is_feishu_docx(files) is False

    def test_real_word_with_empty_styles_but_no_feishu_fingerprints(self):
        """空 styles + 多 lvl 小 ID → 仍不是飞书（指纹 1 和 2 都失败）。

        构造的是个理论边界：styles 是空的（满足必要条件）但 numbering 看起来
        像标准 Word —— 这种情况通常不存在，但要确保不误判。
        """
        files = {
            "word/styles.xml": _FEISHU_EMPTY_STYLES,
            "word/numbering.xml": _REAL_WORD_NUMBERING,
        }
        assert _is_feishu_docx(files) is False

    def test_malformed_numbering_xml(self):
        """损坏的 numbering.xml → ParseError 兜底，返回 False。"""
        files = {
            "word/styles.xml": _FEISHU_EMPTY_STYLES,
            "word/numbering.xml": b"<not valid xml<<>>",
        }
        assert _is_feishu_docx(files) is False

    def test_missing_styles_xml(self):
        """没有 styles.xml 文件 → 长度 0，必要条件满足。"""
        files = {"word/numbering.xml": _FEISHU_NUMBERING}
        assert _is_feishu_docx(files) is True
