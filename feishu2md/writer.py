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
        _write_inplace(content, input_path, backup)
    elif output is not None:
        output.write_text(content, encoding="utf-8", newline="\n")
    else:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stdout.write(content)


def _write_inplace(content: str, input_path: Path | None, backup: bool) -> None:
    """原子写入覆盖原文件。

    流程：
    1. 写入 {input_path}.tmp
    2. backup=True 时重命名原文件为 {input_path}.bak
    3. 重命名 .tmp 为 input_path
    4. backup=False 且存在 .bak 时删除 .bak
    任何步骤失败抛 WriteError，原文件不受影响。
    """
    if input_path is None:
        raise WriteError("inplace=True requires input_path")

    tmp_path = input_path.with_suffix(input_path.suffix + ".tmp")
    bak_path = input_path.with_suffix(".md.bak")

    try:
        # Step 1: 写入临时文件
        tmp_path.write_text(content, encoding="utf-8", newline="\n")
    except OSError as e:
        raise WriteError(f"cannot write to {tmp_path}: {e}") from e

    try:
        # Step 2: 原文件重命名为 .bak
        input_path.rename(bak_path)
    except OSError as e:
        # 清理临时文件
        tmp_path.unlink(missing_ok=True)
        raise WriteError(f"cannot rename {input_path} to {bak_path}: {e}") from e

    try:
        # Step 3: 临时文件重命名为原文件
        tmp_path.rename(input_path)
    except OSError as e:
        # 恢复原文件
        bak_path.rename(input_path)
        raise WriteError(f"cannot rename {tmp_path} to {input_path}: {e}") from e

    # Step 4: 不保留备份时删除 .bak
    if not backup:
        bak_path.unlink(missing_ok=True)
