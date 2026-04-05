"""标题扫描模块。扫描全文收集标题结构信息，判断疑似编号是否构成合理序列。"""

import re

from feishu2md.models import HeadingInfo, LineInfo, ScanResult, Warning

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")


def scan(lines: list[LineInfo]) -> tuple[ScanResult, list[Warning]]:
    """扫描标题行，填充 LineInfo 元数据，返回扫描结果和警告列表。

    当前实现：标题识别、元数据填充、HeadingInfo 列表创建。
    疑似编号提取和序列合理性判断将在后续任务中添加。
    """
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

        # 创建 HeadingInfo
        headings.append(HeadingInfo(
            line_index=i,
            level=level,
            title_text=text,
            suspected_number=None,  # 后续任务实现
        ))

    # 无标题时 min_level 默认为 1
    if not headings:
        min_level = 1

    result = ScanResult(
        headings=headings,
        min_level=min_level,
        is_valid_sequence=False,  # 后续任务实现序列判断
    )

    return result, warnings
