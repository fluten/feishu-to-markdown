"""智能剥离模块。根据扫描结果和用户参数，决定并执行编号剥离。"""

from feishu2md.models import LineInfo, ScanResult, Warning


def strip(
    lines: list[LineInfo],
    scan_result: ScanResult,
    mode: str,
) -> tuple[list[LineInfo], ScanResult, list[Warning]]:
    """剥离标题中的已有编号，返回更新后的 lines、scan_result 和警告列表。"""
    pass
