"""标题扫描模块。扫描全文收集标题结构信息，判断疑似编号是否构成合理序列。"""

import re

from feishu2md.models import HeadingInfo, LineInfo, ScanResult, Warning

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")

# 疑似编号提取正则（模块顶层预编译）
_NUM_DOT_RE = re.compile(r"^(\d+(?:\.\d+)*)\s+")       # 1 / 1.1 / 1.1.1
_NUM_PAREN_RE = re.compile(r"^[（(](\d+)[)）]\s*")       # (1) / （3）
_CN_NUM_RE = re.compile(r"^[一二三四五六七八九十百]+、")    # 一、 / 十二、
_CN_PAREN_RE = re.compile(r"^[（(][一二三四五六七八九十百]+[)）]\s*")  # （一） / (三)


def scan(lines: list[LineInfo]) -> tuple[ScanResult, list[Warning]]:
    """扫描标题行，填充 LineInfo 元数据，返回扫描结果和警告列表。"""
    warnings: list[Warning] = []
    headings: list[HeadingInfo] = []
    min_level = 6

    for i, line in enumerate(lines):
        # 跳过受保护区域和 blockquote
        if line.is_protected or line.is_blockquote:
            continue

        match = _HEADING_RE.match(line.raw_text)
        if not match:
            continue

        hashes = match.group(1)
        text = match.group(2).strip()
        level = len(hashes)

        # 空标题（# 后只有空白）不识别
        if not text:
            continue

        # 填充 LineInfo 元数据
        line.heading_level = level
        line.heading_text = text

        if level < min_level:
            min_level = level

        # 提取疑似编号
        suspected = _extract_suspected_number(text)

        # 创建 HeadingInfo
        headings.append(HeadingInfo(
            line_index=i,
            level=level,
            title_text=text,
            suspected_number=suspected,
        ))

    # 无标题时 min_level 默认为 1
    if not headings:
        min_level = 1

    # 序列合理性判断
    is_valid = _check_sequence_validity(headings)

    # 不合理序列但有疑似编号时，返回 Info 级 Warning
    if not is_valid and any(h.suspected_number is not None for h in headings):
        warnings.append(Warning(
            line_number=0,
            message=(
                "number prefixes detected but not a valid numbering sequence, "
                "skipping strip. Use --force-strip to override."
            ),
        ))

    result = ScanResult(
        headings=headings,
        min_level=min_level,
        is_valid_sequence=is_valid,
    )

    return result, warnings


def _extract_suspected_number(text: str) -> str | None:
    """从标题文本中提取疑似编号字符串。返回匹配到的编号或 None。

    只提取纯数字点号格式（1 / 1.1 / 1.1.1），因为这是唯一需要上下文校验的格式。
    中文编号和括号编号不需要上下文校验（直接剥离），所以不在此处提取。
    """
    m = _NUM_DOT_RE.match(text)
    if m:
        return m.group(1)
    return None


def _check_sequence_validity(headings: list[HeadingInfo]) -> bool:
    """判断疑似编号是否构成合理的编号序列。

    三条规则全部满足才返回 True：
    1. 同级编号连续递增（允许间隔，不允许乱序）
    2. 子级编号父级前缀与实际父标题编号一致
    3. 至少 50% 标题包含疑似编号
    """
    if not headings:
        return False

    numbered = [h for h in headings if h.suspected_number is not None]
    if not numbered:
        return False

    # 规则 3：至少 50% 标题包含疑似编号
    if len(numbered) / len(headings) < 0.5:
        return False

    # 规则 1：同级编号连续递增（允许间隔，不允许乱序）
    # 遇到高级标题时重置低级标题的计数器（编号在新的父级下重新开始）
    level_last_numbers: dict[int, int] = {}
    for h in numbered:
        parts = h.suspected_number.split(".")
        level_num = int(parts[-1])
        level = h.level

        # 遇到某层级时，清除更低层级的记录（低级编号在新父级下重置）
        levels_to_clear = [lv for lv in level_last_numbers if lv > level]
        for lv in levels_to_clear:
            del level_last_numbers[lv]

        if level in level_last_numbers:
            if level_num <= level_last_numbers[level]:
                # 乱序：当前编号 <= 上一个同级编号
                return False
        level_last_numbers[level] = level_num

    # 规则 2：子级编号父级前缀与实际父标题编号一致
    # 构建当前各层级的编号，检查子级编号的前缀
    current_numbers: dict[int, str] = {}
    for h in numbered:
        num = h.suspected_number
        parts = num.split(".")
        level = h.level

        if len(parts) > 1:
            # 子级编号：检查父级前缀
            parent_prefix = ".".join(parts[:-1])
            parent_level = level - 1
            if parent_level in current_numbers:
                if current_numbers[parent_level] != parent_prefix:
                    return False

        current_numbers[level] = num
        # 遇到某层级编号时，清除更低层级的记录（编号重置）
        levels_to_clear = [lv for lv in current_numbers if lv > level]
        for lv in levels_to_clear:
            del current_numbers[lv]

    return True
