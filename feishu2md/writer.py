"""输出模块。将处理结果写入目标位置。"""

import sys
from pathlib import Path

from feishu2md.models import LineInfo, WriteError


def write(
    lines: list[LineInfo],
    output: Path | None,
    inplace: bool,
    backup: bool,
    input_path: Path | None = None,
) -> None:
    """将处理结果输出到 stdout、文件或原地覆盖。"""
    content = "\n".join(line.raw_text for line in lines)

    if inplace:
        # inplace 原子写入（后续任务实现）
        pass
    elif output is not None:
        # 文件输出
        output.write_text(content, encoding="utf-8", newline="\n")
    else:
        # stdout 输出
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stdout.write(content)
