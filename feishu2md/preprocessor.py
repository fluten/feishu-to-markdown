"""预处理模块。将原始文本转换为标记好受保护区域的行列表，并完成 Setext → ATX 转换。"""

import re

from feishu2md.models import LineInfo

_FRONT_MATTER_CLOSE_RE = re.compile(r"^---\s*$")
_CODE_FENCE_RE = re.compile(r"^(`{3,}|~{3,})")
_HTML_COMMENT_OPEN = "<!--"
_HTML_COMMENT_CLOSE = "-->"
_SETEXT_H1_RE = re.compile(r"^={3,}\s*$")
_SETEXT_H2_RE = re.compile(r"^-{3,}\s*$")

# 飞书导出 docx 经 Pandoc 转换后的粗体标题模式：
# "1\. **文档信息**" / "2.1 **定位**" / "3.1.1 **背景**"
_FEISHU_BOLD_HEADING_RE = re.compile(
    r"^(\d+(?:\.\d+)*)\\?\.\s+\*\*(.+?)\*\*\s*$"  # N\. **text** 格式（顶层）
)
_FEISHU_BOLD_HEADING_SUB_RE = re.compile(
    r"^(\d+\.\d+(?:\.\d+)*)\s+\*\*(.+?)\*\*\s*$"   # N.N / N.N.N **text** 格式（子层级）
)
# 飞书文档标题：独立的 **纯粗体行**，无编号前缀，无其他文本
_FEISHU_BOLD_TITLE_RE = re.compile(r"^\*\*(.+?)\*\*\s*$")


def preprocess(content: str) -> list[LineInfo]:
    """将原始文本转换为 LineInfo 列表。

    处理流程：换行符统一 → 行分割 → 受保护区域标记 → Setext → ATX 转换。
    """
    # 1. 统一换行符
    content = content.replace("\r\n", "\n")

    # 2. 按 \n 分割，创建 LineInfo（line_number 1-based）
    raw_lines = content.split("\n")
    lines = [
        LineInfo(line_number=i + 1, raw_text=text)
        for i, text in enumerate(raw_lines)
    ]

    # 3. 受保护区域标记
    _mark_protected_regions(lines)

    # 4. 飞书粗体标题转换（数字编号 + **粗体** → ATX 标题）
    _convert_feishu_bold_headings(lines)

    # 5. Setext → ATX 标题转换
    lines = _convert_setext_to_atx(lines)

    return lines


def _mark_protected_regions(lines: list[LineInfo]) -> None:
    """顺序扫描并标记受保护区域和 blockquote 行。

    受保护区域（is_protected=True）：
    - Front matter（文件开头 --- ... ---）
    - 代码块（``` 或 ~~~ 包裹，支持多重反引号）
    - HTML 注释（<!-- ... -->，支持跨行）

    Blockquote（is_blockquote=True）：
    - 以 > 开头的行
    """
    in_code_block = False
    code_fence_char = ""
    code_fence_count = 0

    in_html_comment = False

    # --- Front matter ---
    # 仅文件开头的 ---...---，开头行必须是恰好 ---
    start_idx = 0
    if lines and _FRONT_MATTER_CLOSE_RE.match(lines[0].raw_text):
        lines[0].is_protected = True
        for i in range(1, len(lines)):
            lines[i].is_protected = True
            if _FRONT_MATTER_CLOSE_RE.match(lines[i].raw_text):
                start_idx = i + 1
                break
        else:
            # 没有找到关闭标记，整个文件都是 front matter（异常但不崩溃）
            return

    # --- 代码块 / HTML 注释 / blockquote ---
    for i in range(start_idx, len(lines)):
        line = lines[i]
        text = line.raw_text

        # HTML 注释跨行处理
        if in_html_comment:
            line.is_protected = True
            if _HTML_COMMENT_CLOSE in text:
                in_html_comment = False
            continue

        # 代码块开闭
        if in_code_block:
            line.is_protected = True
            fence_match = _CODE_FENCE_RE.match(text)
            if fence_match:
                fence = fence_match.group(1)
                # 关闭条件：相同字符、数量 >= 开启数量、行上仅有 fence + 可选空白
                if (
                    fence[0] == code_fence_char
                    and len(fence) >= code_fence_count
                    and text.strip() == fence
                ):
                    in_code_block = False
            continue

        # 检查代码块开启
        fence_match = _CODE_FENCE_RE.match(text)
        if fence_match:
            fence = fence_match.group(1)
            in_code_block = True
            code_fence_char = fence[0]
            code_fence_count = len(fence)
            line.is_protected = True
            continue

        # 检查 HTML 注释（单行或多行开启）
        if _HTML_COMMENT_OPEN in text:
            # 单行注释：同一行内开闭
            if _HTML_COMMENT_CLOSE in text[text.index(_HTML_COMMENT_OPEN) + 4:]:
                line.is_protected = True
                continue
            # 多行注释开启
            in_html_comment = True
            line.is_protected = True
            continue

        # Blockquote 标记
        if text.startswith(">"):
            line.is_blockquote = True


def _convert_setext_to_atx(lines: list[LineInfo]) -> list[LineInfo]:
    """将 Setext 风格标题转换为 ATX 风格。

    转换规则：
    - 非空文本行 + ===（≥3个）→ # 文本
    - 非空文本行 + ---（≥3个）→ ## 文本
    约束：
    - 前一行非空且紧邻（前面是空行则不转换）
    - 受保护区域内不转换
    - 转换后删除下划线行，保留原始 line_number
    """
    if len(lines) < 2:
        return lines

    indices_to_remove: list[int] = []

    for i in range(1, len(lines)):
        underline = lines[i]
        prev = lines[i - 1]

        # 受保护区域内不转换
        if underline.is_protected or prev.is_protected:
            continue

        # blockquote 内不转换
        if underline.is_blockquote or prev.is_blockquote:
            continue

        # 前一行必须非空
        if not prev.raw_text.strip():
            continue

        text = underline.raw_text

        # 检查 === 或 ---
        if _SETEXT_H1_RE.match(text):
            prev.raw_text = f"# {prev.raw_text}"
            indices_to_remove.append(i)
        elif _SETEXT_H2_RE.match(text):
            prev.raw_text = f"## {prev.raw_text}"
            indices_to_remove.append(i)

    # 从后往前删除，避免索引偏移
    for i in reversed(indices_to_remove):
        del lines[i]

    return lines


def _convert_feishu_bold_headings(lines: list[LineInfo]) -> None:
    """将飞书导出 docx 经 Pandoc 转换后的粗体标题模式转换为 ATX 标题。

    飞书导出的 docx 不使用 Word 标题样式，而是用粗体文本 + 手动编号。
    Pandoc 转换后变成：
      **文档标题**          → 应转为 # 文档标题（文档第一个纯粗体行）
      1\\. **文档信息**     → 应转为 # 文档信息
      2.1 **定位**          → 应转为 ## 定位
      3.1.1 **背景**        → 应转为 ### 背景

    编号段数决定标题层级：1段=H1, 2段=H2, 3段=H3, ...
    编号被剥离（后续由 numbering 模块重新生成），粗体标记也被剥离。
    文档标题（第一个编号标题之前的独立纯粗体行）被识别为 H1。
    """
    # 先扫描：文档是否包含飞书编号标题？
    has_feishu_headings = any(
        not line.is_protected and not line.is_blockquote and (
            _FEISHU_BOLD_HEADING_RE.match(line.raw_text) or
            _FEISHU_BOLD_HEADING_SUB_RE.match(line.raw_text)
        )
        for line in lines
    )
    if not has_feishu_headings:
        return

    # 检测文档标题：第一个编号标题之前的独立纯粗体行
    has_title = False
    for line in lines:
        if line.is_protected or line.is_blockquote:
            continue
        text = line.raw_text
        if not text.strip():
            continue
        # 如果第一个非空行是纯粗体（无编号），则为文档标题
        if _FEISHU_BOLD_TITLE_RE.match(text) and not _FEISHU_BOLD_HEADING_RE.match(text):
            has_title = True
        break  # 只检查第一个非空行

    # 有文档标题时，编号标题全部降一级（标题占 H1）
    level_offset = 1 if has_title else 0
    found_numbered = False

    for line in lines:
        if line.is_protected or line.is_blockquote:
            continue

        text = line.raw_text

        # 尝试匹配 "N\. **text**" 格式（顶层，Pandoc 转义了点号）
        m = _FEISHU_BOLD_HEADING_RE.match(text)
        if m:
            found_numbered = True
            number_str = m.group(1)
            heading_text = m.group(2)
            level = len(number_str.split(".")) + level_offset
            prefix = "#" * level
            line.raw_text = f"{prefix} {heading_text}"
            continue

        # 尝试匹配 "N.N **text**" / "N.N.N **text**" 格式（子层级）
        m = _FEISHU_BOLD_HEADING_SUB_RE.match(text)
        if m:
            found_numbered = True
            number_str = m.group(1)
            heading_text = m.group(2)
            level = len(number_str.split(".")) + level_offset
            prefix = "#" * level
            line.raw_text = f"{prefix} {heading_text}"
            continue

        # 文档标题：保持 **粗体** 原样不转换。
        # 它在 Markdown 渲染时显示为粗体文本（视觉上是标题效果），
        # 但不参与 scanner/numbering 的编号系统。
