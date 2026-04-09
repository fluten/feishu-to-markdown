"""修补飞书导出的 .docx，恢复 Pandoc 丢失的标题层级与列表小标号。

飞书导出的 docx 有两个反常之处导致 Pandoc 不能正确解析：

1. **styles.xml 是空的**（仅 121 字节的 `<w:styles/>`），但 document.xml 里仍然
   引用 `<w:pStyle w:val="1"/>` 到 `"6"`。Pandoc 找不到样式定义，把这些段落当成
   普通粗体段落处理，标题层级丢失。

2. **列表项各自独立**：每个列表项分配独立的 `numId`，对应的 `abstractNum` 把
   显示数字硬编码在 `<w:start w:val="N"/>` 里，而不是用计数器。Pandoc 期望多个
   段落共享同一个 numId 由计数器累加，于是干脆放弃这种"每段一个 numId"的列表，
   编号、嵌套层级全部丢失。

本模块的修补策略：

- **Step A** —— 注入 6 条标准 Heading 1..6 样式定义。Pandoc 看到
  `pStyle val="1"` 能在 styles.xml 找到 `<w:name w:val="Heading 1"/>` →
  输出 `# 标题`。

- **Step B** —— 解析 numbering.xml，为每个带 `<w:numPr>` 的段落计算"应显示的
  编号文本"（例如 "1." / "a." / "-"）和嵌套深度（基于 `<w:ind w:left="N"/>`，
  453 twips ≈ 1 级缩进）。把这两部分作为一个文本运行注入到段落开头，编码为
  `FZmark{depth}Zf{prefix}` 的形式，然后从 pPr 里删除 numPr 和 ind。Pandoc
  把整个段落当普通文本输出，编号和层级以 marker 形式幸存。

- **post_process_markers** —— Pandoc 跑完后，扫描 markdown 行：
  - 如果 marker 在行首（普通段落上下文）→ 用 `4 * depth` 个空格做缩进，并
    还原 pandoc 对 `1.` `a.` `-` 加的反斜杠转义；
  - 如果 marker 在行内（HTML 表格单元上下文）→ 用 `&nbsp; * 4 * depth` 缩进，
    因为 HTML 折叠真实空格。

**飞书指纹判定**（`_is_feishu_docx`）：Step A 和 Step B 共用同一个 gate。
判定逻辑：
1. 必要条件：`styles.xml` 是空的（< 300 字节）—— 这是飞书最稳的指纹，
   标准 Word 文档总是有完整的样式定义；
2. 如果文档有 numbering.xml，还要满足下列任一：
   - 存在 `abstractNumId >= 1000` 的 abstractNum（飞书用 656820+，Word 一般 0-100）
   - 每个 abstractNum 都恰好只有一个 `<w:lvl>`（飞书的"每段独立 lvl"特征）
3. 如果文档没有 numbering.xml（飞书只用了标题没有列表），仅靠条件 1 即可判定。

对非飞书 docx 模块完全 no-op：直接 `shutil.copy` 输入到输出，不做任何 patch。
"""
import re
import shutil
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_INDENT_TWIPS = 453  # 1 indent level in Feishu defaults
_FEISHU_STYLES_THRESHOLD = 300  # 字节阈值，判定飞书空 styles.xml


# 注入到空 styles.xml 的 6 条 heading 定义。
# 关键点：必须用 `Heading 1` 等大写 H 的 name 才能被 pandoc 识别为标题样式。
_HEADING_STYLES_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>
  <w:style w:type="paragraph" w:styleId="1"><w:name w:val="Heading 1"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:pPr><w:outlineLvl w:val="0"/></w:pPr></w:style>
  <w:style w:type="paragraph" w:styleId="2"><w:name w:val="Heading 2"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:pPr><w:outlineLvl w:val="1"/></w:pPr></w:style>
  <w:style w:type="paragraph" w:styleId="3"><w:name w:val="Heading 3"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:pPr><w:outlineLvl w:val="2"/></w:pPr></w:style>
  <w:style w:type="paragraph" w:styleId="4"><w:name w:val="Heading 4"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:pPr><w:outlineLvl w:val="3"/></w:pPr></w:style>
  <w:style w:type="paragraph" w:styleId="5"><w:name w:val="Heading 5"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:pPr><w:outlineLvl w:val="4"/></w:pPr></w:style>
  <w:style w:type="paragraph" w:styleId="6"><w:name w:val="Heading 6"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:pPr><w:outlineLvl w:val="5"/></w:pPr></w:style>
</w:styles>
"""


# ============================================================
# 编号渲染
# ============================================================


def _to_roman(n: int) -> str:
    vals = [(1000, "M"), (900, "CM"), (500, "D"), (400, "CD"),
            (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
            (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]
    out = ""
    for v, sym in vals:
        while n >= v:
            out += sym
            n -= v
    return out


def _render_number(num_fmt: str, start: int) -> str:
    """根据 numFmt 和 start 值渲染编号字符串。"""
    if num_fmt == "decimal":
        return str(start)
    if num_fmt == "lowerLetter":
        return chr(ord("a") + (start - 1) % 26)
    if num_fmt == "upperLetter":
        return chr(ord("A") + (start - 1) % 26)
    if num_fmt == "lowerRoman":
        return _to_roman(start).lower()
    if num_fmt == "upperRoman":
        return _to_roman(start)
    if num_fmt == "bullet":
        return ""  # bullets handled separately
    return str(start)


# ============================================================
# numbering.xml 解析（只读，使用 ET 安全）
# ============================================================


def _parse_numbering_xml(xml_bytes: bytes) -> dict[str, tuple[str, int, str]]:
    """返回 {numId: (numFmt, start, lvlText)}。

    飞书的每个 abstractNum 通常只包含一个 `<w:lvl>`，把可见的计数硬编码在
    `start` 里。我们走 numId → abstractNumId → 第一个 lvl。
    """
    if not xml_bytes:
        return {}
    root = ET.fromstring(xml_bytes)

    abstract: dict[str, tuple[str, int, str]] = {}
    for an in root.findall(_W + "abstractNum"):
        aid = an.get(_W + "abstractNumId")
        lvl = an.find(_W + "lvl")
        if lvl is None:
            continue
        nf = lvl.find(_W + "numFmt")
        st = lvl.find(_W + "start")
        lt = lvl.find(_W + "lvlText")
        num_fmt = nf.get(_W + "val") if nf is not None else "decimal"
        start = int(st.get(_W + "val")) if st is not None else 1
        lvl_text = lt.get(_W + "val") if lt is not None else "%1."
        abstract[aid] = (num_fmt, start, lvl_text)

    num_map: dict[str, tuple[str, int, str]] = {}
    for n in root.findall(_W + "num"):
        nid = n.get(_W + "numId")
        ani = n.find(_W + "abstractNumId")
        if ani is None:
            continue
        aid = ani.get(_W + "val")
        if aid in abstract:
            num_map[nid] = abstract[aid]
    return num_map


# ============================================================
# document.xml 字符串手术
# ============================================================
#
# 用字符串/正则手术而不是 ET round-trip 是因为 stdlib ET 序列化会把
# 未注册的命名空间（r:、wp:、a:、pic: 等）重命名为 ns1/ns2/...，破坏
# pandoc 对超链接、图片、绘图等元素的解析。字符串手术保证其余内容
# 一字节不动。

_PARA_RE = re.compile(r"<w:p(?:\s[^>]*)?>.*?</w:p>", re.DOTALL)
_PPR_RE = re.compile(r"<w:pPr(?:\s[^>]*)?>.*?</w:pPr>", re.DOTALL)
_NUMPR_RE = re.compile(r"<w:numPr(?:\s[^>]*)?>.*?</w:numPr>", re.DOTALL)
_IND_RE = re.compile(r"<w:ind(?:\s[^>]*?)?(?:/>|>.*?</w:ind>)", re.DOTALL)
_IND_LEFT_RE = re.compile(r'<w:ind[^>]*?w:left="(\d+)"')
_NUMID_VAL_RE = re.compile(r'<w:numId\s+w:val="([^"]+)"')


def _patch_paragraph(p_xml: str, num_map: dict) -> str:
    """对单个 `<w:p>` 段落执行 Step B 手术。"""
    pPr_match = _PPR_RE.search(p_xml)
    if not pPr_match:
        return p_xml

    pPr = pPr_match.group()
    if "<w:numPr" not in pPr:
        return p_xml

    numPr_match = _NUMPR_RE.search(pPr)
    numPr = numPr_match.group() if numPr_match else ""
    nid_match = _NUMID_VAL_RE.search(numPr)
    nid = nid_match.group(1) if nid_match else None

    # 提取 ind.left 计算嵌套深度
    ind_left = 0
    ind_match = _IND_LEFT_RE.search(pPr)
    if ind_match:
        try:
            ind_left = int(ind_match.group(1))
        except ValueError:
            ind_left = 0
    depth = max(0, round(ind_left / _INDENT_TWIPS))

    # 计算前缀文本
    prefix = ""
    if nid and nid in num_map:
        num_fmt, start, lvl_text = num_map[nid]
        if num_fmt == "bullet":
            prefix = "- "
        else:
            value = _render_number(num_fmt, start)
            if value:
                prefix = lvl_text.replace("%1", value) + " "

    # 从 pPr 里删除 numPr 和 ind
    new_pPr = _NUMPR_RE.sub("", pPr)
    new_pPr = _IND_RE.sub("", new_pPr)
    new_p = p_xml.replace(pPr, new_pPr, 1)

    # 在 </w:pPr> 后插入「深度标记 + 前缀」文本运行。
    # FZmark{depth}Zf 是纯 ASCII，不会被 pandoc 当 markdown 语法处理。
    if prefix:
        marker = f"FZmark{depth}Zf"
        prefix_xml = (
            f'<w:r><w:t xml:space="preserve">{marker}{prefix}</w:t></w:r>'
        )
        new_p = new_p.replace("</w:pPr>", "</w:pPr>" + prefix_xml, 1)

    return new_p


def _patch_document_xml(doc_xml: str, num_map: dict) -> str:
    """对整个 document.xml 执行字符串手术。"""
    return _PARA_RE.sub(lambda m: _patch_paragraph(m.group(), num_map), doc_xml)


# ============================================================
# 飞书指纹检测
# ============================================================


# 飞书的 abstractNumId 用大数字（实测 656820+），标准 Word 一般 0-100
_FEISHU_ABSTRACT_ID_THRESHOLD = 1000


def _is_feishu_docx(files: dict) -> bool:
    """根据 docx 内容判定是否飞书导出。

    判定逻辑（详见模块 docstring）：
    - 必要条件：styles.xml 是空的（< 300 字节）
    - 如果有 numbering.xml，还需满足以下任一：
      - 存在 abstractNumId >= 1000 的 abstractNum
      - 每个 abstractNum 都恰好只有一个 <w:lvl>
    - 如果没有 numbering.xml，仅凭空 styles.xml 即判定为飞书

    返回 False 时，patch_docx 会变成 no-op（直接复制输入到输出）。
    """
    # 必要条件：空 styles.xml
    styles = files.get("word/styles.xml", b"")
    if len(styles) >= _FEISHU_STYLES_THRESHOLD:
        return False

    numbering = files.get("word/numbering.xml", b"")
    if not numbering:
        # 没有 numbering.xml，仅凭空 styles 已足够
        return True

    try:
        root = ET.fromstring(numbering)
    except ET.ParseError:
        return False

    abstract_nums = root.findall(_W + "abstractNum")
    if not abstract_nums:
        # numbering.xml 存在但没有 abstractNum 定义，仅凭空 styles 已足够
        return True

    # 指纹 1：abstractNumId 是大数字
    for an in abstract_nums:
        aid = an.get(_W + "abstractNumId")
        if aid and aid.isdigit() and int(aid) >= _FEISHU_ABSTRACT_ID_THRESHOLD:
            return True

    # 指纹 2：每个 abstractNum 都恰好只有一个 <w:lvl>
    if all(len(an.findall(_W + "lvl")) == 1 for an in abstract_nums):
        return True

    return False


# ============================================================
# 入口：patch_docx
# ============================================================


def patch_docx(input_path: Path, output_path: Path) -> None:
    """读入 input_path，把修补后的 docx 写到 output_path。

    对非飞书 docx 是完全 no-op：直接复制输入到输出。检测条件见
    `_is_feishu_docx()`。

    对飞书 docx 同时执行 Step A（注入 heading 样式）和 Step B（解析
    numbering.xml + 字符串手术修补 document.xml）。
    """
    with zipfile.ZipFile(input_path, "r") as zin:
        files: dict[str, bytes] = {name: zin.read(name) for name in zin.namelist()}

    if not _is_feishu_docx(files):
        # 非飞书 docx：直接拷贝原文件，不做任何 patch
        shutil.copy(input_path, output_path)
        return

    # Step A: 注入 heading 样式定义
    files["word/styles.xml"] = _HEADING_STYLES_XML.encode("utf-8")

    # Step B: 解析 numbering.xml + 字符串手术修补 document.xml
    num_map = _parse_numbering_xml(files.get("word/numbering.xml", b""))
    if "word/document.xml" in files:
        doc_xml = files["word/document.xml"].decode("utf-8")
        doc_xml = _patch_document_xml(doc_xml, num_map)
        files["word/document.xml"] = doc_xml.encode("utf-8")

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zout:
        for name, data in files.items():
            zout.writestr(name, data)


# ============================================================
# Markdown 后处理：还原 marker 为缩进
# ============================================================
#
# 两种情况：
# 1) marker 在行首 → 普通段落，用 4*depth 真空格缩进
# 2) marker 在 <p>...</p> 等行内位置 → HTML 表格单元，用 &nbsp; 缩进
#    （HTML 折叠真空格）

_LINE_START_MARKER_RE = re.compile(r"^(\s*)FZmark(\d+)Zf")
_ANY_MARKER_RE = re.compile(r"FZmark(\d+)Zf")
_ESCAPED_NUM_RE = re.compile(r"^(\d+)\\\.\s")
_ESCAPED_LETTER_RE = re.compile(r"^([a-zA-Z])\\\.\s")
_ESCAPED_BULLET_RE = re.compile(r"^\\-\s")


def post_process_markers(md: str) -> str:
    """把 markdown 里的 FZmark 标记还原成实际的缩进。"""
    lines = md.split("\n")
    out: list[str] = []
    for line in lines:
        m = _LINE_START_MARKER_RE.match(line)
        if m:
            # 情况 1：行首 marker（普通段落）
            depth = int(m.group(2))
            rest = line[m.end():]
            # 还原 pandoc 对列表标记的反斜杠转义
            rest = _ESCAPED_BULLET_RE.sub("- ", rest, count=1)
            rest = _ESCAPED_NUM_RE.sub(lambda x: x.group(1) + ". ", rest, count=1)
            rest = _ESCAPED_LETTER_RE.sub(lambda x: x.group(1) + ". ", rest, count=1)
            line = "    " * depth + rest

        # 情况 2：行内 / HTML 上下文里的 marker → 用 &nbsp; 缩进
        if "FZmark" in line:
            line = _ANY_MARKER_RE.sub(
                lambda x: "&nbsp;" * (int(x.group(1)) * 4), line
            )
        out.append(line)
    return "\n".join(out)
