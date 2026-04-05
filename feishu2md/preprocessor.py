"""预处理模块。将原始文本转换为标记好受保护区域的行列表，并完成 Setext → ATX 转换。"""

from feishu2md.models import LineInfo


def preprocess(content: str) -> list[LineInfo]:
    """将原始文本转换为 LineInfo 列表。"""
    pass
