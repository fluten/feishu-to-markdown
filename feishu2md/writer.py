"""输出模块。将处理结果写入目标位置。"""

from pathlib import Path

from feishu2md.models import LineInfo


def write(
    lines: list[LineInfo],
    output: Path | None,
    inplace: bool,
    backup: bool,
    input_path: Path | None = None,
) -> None:
    """将处理结果输出到 stdout、文件或原地覆盖。"""
    pass
