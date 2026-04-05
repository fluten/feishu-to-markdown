"""编号生成模块。根据标题层级为标题添加编号前缀。"""

from feishu2md.models import LineInfo, ScanResult, Warning


def generate(
    lines: list[LineInfo],
    scan_result: ScanResult,
    max_level: int,
) -> tuple[list[LineInfo], list[Warning]]:
    """为标题生成层级编号，返回更新后的 lines 和警告列表。"""
    pass
