"""Pandoc 调用模块。封装所有 Pandoc 相关操作。"""

from pathlib import Path


def convert(docx_path: Path, output_dir: Path | None = None) -> str:
    """将 .docx 文件通过 Pandoc 转换为 Markdown 文本。"""
    pass
