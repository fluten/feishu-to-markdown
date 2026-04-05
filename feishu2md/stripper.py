"""智能剥离模块。根据扫描结果和用户参数，决定并执行编号剥离。"""

import re

from feishu2md.models import LineInfo, ScanResult, Warning

# 剥离用正则（模块顶层预编译）
# 纯数字点号：1 / 1.1 / 1.1.1（后跟至少一个空白）
_NUM_DOT_RE = re.compile(r"^\d+(?:\.\d+)*\s+")
# 带括号数字：(1) / （3）（后跟可选空白）
_NUM_PAREN_RE = re.compile(r"^[（(]\d+[)）]\s*")
# 中文数字：一、 / 十二、
_CN_NUM_RE = re.compile(r"^[一二三四五六七八九十百]+、\s*")
# 中文带括号：（一） / (三)（后跟可选空白）
_CN_PAREN_RE = re.compile(r"^[（(][一二三四五六七八九十百]+[)）]\s*")

_ALL_PATTERNS = [_NUM_DOT_RE, _NUM_PAREN_RE, _CN_NUM_RE, _CN_PAREN_RE]
_CHINESE_ONLY_PATTERNS = [_CN_NUM_RE, _CN_PAREN_RE]


def strip(
    lines: list[LineInfo],
    scan_result: ScanResult,
    mode: str,
) -> tuple[list[LineInfo], ScanResult, list[Warning]]:
    """剥离标题中的已有编号，返回更新后的 lines、scan_result 和警告列表。

    mode 取值：
    - 'none': 跳过所有剥离
    - 'force': 强制剥离所有格式编号
    - 'auto': 智能剥离（合理序列→全部剥离，否则仅剥离中文编号）
    - 'strip_only': 剥离逻辑同 auto
    """
    warnings: list[Warning] = []

    if mode == "none":
        return lines, scan_result, warnings

    # 确定要使用的剥离正则列表
    if mode == "force":
        patterns = _ALL_PATTERNS
    else:
        # auto / strip_only
        if scan_result.is_valid_sequence:
            patterns = _ALL_PATTERNS
        else:
            patterns = _CHINESE_ONLY_PATTERNS

    # 构建 line_index → HeadingInfo 的映射，用于同步更新
    heading_map = {h.line_index: h for h in scan_result.headings}

    # 遍历所有标题行执行剥离
    for i, line in enumerate(lines):
        if line.heading_level is None:
            continue

        old_text = line.heading_text
        new_text = _strip_number_prefix(old_text, patterns)

        if new_text != old_text:
            # 同步更新三处数据
            line.heading_text = new_text
            line.raw_text = _rebuild_raw_text(line.heading_level, new_text)
            if i in heading_map:
                heading_map[i].title_text = new_text

    return lines, scan_result, warnings


def _strip_number_prefix(text: str, patterns: list[re.Pattern]) -> str:
    """从标题文本开头去除匹配的编号前缀。只尝试第一个匹配的正则。"""
    for pattern in patterns:
        m = pattern.match(text)
        if m:
            return text[m.end():]
    return text


def _rebuild_raw_text(level: int, heading_text: str) -> str:
    """根据标题层级和新的 heading_text 重建 raw_text。"""
    prefix = "#" * level
    return f"{prefix} {heading_text}"
