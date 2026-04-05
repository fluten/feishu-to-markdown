"""预处理模块。将原始文本转换为标记好受保护区域的行列表，并完成 Setext → ATX 转换。"""

import re

from feishu2md.models import LineInfo

_FRONT_MATTER_CLOSE_RE = re.compile(r"^---\s*$")
_CODE_FENCE_RE = re.compile(r"^(`{3,}|~{3,})")
_HTML_COMMENT_OPEN = "<!--"
_HTML_COMMENT_CLOSE = "-->"


def preprocess(content: str) -> list[LineInfo]:
    """将原始文本转换为 LineInfo 列表。

    当前实现：换行符统一、行分割、受保护区域标记。
    Setext → ATX 转换将在后续任务中添加。
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
