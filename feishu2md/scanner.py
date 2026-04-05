"""标题扫描模块。扫描全文收集标题结构信息，判断疑似编号是否构成合理序列。"""

from feishu2md.models import LineInfo, ScanResult, Warning


def scan(lines: list[LineInfo]) -> tuple[ScanResult, list[Warning]]:
    """扫描标题行，返回扫描结果和警告列表。"""
    pass
