"""编号生成模块。根据标题层级为标题添加编号前缀。"""

from feishu2md.models import LineInfo, ScanResult, Warning


def generate(
    lines: list[LineInfo],
    scan_result: ScanResult,
    max_level: int,
) -> tuple[list[LineInfo], list[Warning]]:
    """为标题生成层级编号，返回更新后的 lines 和警告列表。"""
    warnings: list[Warning] = []
    min_level = scan_result.min_level
    counters = [0] * max_level
    prev_index = -1  # 上一个编号标题的计数器索引

    for line in lines:
        if line.heading_level is None:
            continue

        level = line.heading_level
        index = level - min_level  # 基于 min_level 偏移

        # 超过 max_level 的标题不编号
        if index >= max_level or index < 0:
            continue

        # 层级跳跃检测：如果跳过了中间层级，补 1
        if prev_index >= 0 and index > prev_index + 1:
            for gap in range(prev_index + 1, index):
                if gap < max_level:
                    counters[gap] = 1
            warnings.append(Warning(
                line_number=line.line_number,
                message=(
                    f"heading level jumped from H{min_level + prev_index} "
                    f"to H{level} at line {line.line_number}, "
                    f"auto-filled H{min_level + prev_index + 1} counter"
                ),
            ))

        # 当前层级 +1
        counters[index] += 1
        # 下级归零
        for j in range(index + 1, max_level):
            counters[j] = 0

        prev_index = index

        # 生成编号字符串
        number = ".".join(str(counters[k]) for k in range(index + 1))

        # 拼接编号前缀，同步更新 heading_text 和 raw_text
        line.heading_text = f"{number} {line.heading_text}"
        prefix = "#" * level
        line.raw_text = f"{prefix} {line.heading_text}"

    return lines, warnings
