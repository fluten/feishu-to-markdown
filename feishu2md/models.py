"""共享数据结构和异常定义。所有模块之间通过这些 dataclass 通信。"""

from dataclasses import dataclass

# ============================================================
# 核心数据结构
# ============================================================


@dataclass
class LineInfo:
    """单行信息，贯穿整个流水线的核心数据单元"""
    line_number: int              # 原始文件行号（1-based，用于错误提示，不用于定位）
    raw_text: str                 # 当前文本内容（可被各阶段修改）
    is_protected: bool = False    # 是否在受保护区域内（代码块/HTML注释/front matter）
    is_blockquote: bool = False   # 是否在 blockquote 内
    heading_level: int | None = None   # 标题层级（1-6），None 表示非标题行
    heading_text: str | None = None    # 标题纯文本（去掉 # 前缀和编号后的内容），非标题行为 None


@dataclass
class HeadingInfo:
    """标题行的扫描信息（scanner 输出）"""
    line_index: int               # 在 lines 列表中的索引（指向预处理后的列表，非原始行号）
    level: int                    # 标题层级（1-6）
    title_text: str               # 标题纯文本（去掉 # 前缀）
    suspected_number: str | None  # 疑似编号（如 "1.1"），None 表示没有


@dataclass
class ScanResult:
    """标题扫描结果"""
    headings: list[HeadingInfo]   # 所有标题信息
    min_level: int                # 文档最高出现的标题层级
    is_valid_sequence: bool       # 疑似编号是否构成合理序列


@dataclass
class Warning:
    """模块产生的警告信息，由编排层统一输出到 stderr"""
    line_number: int              # 原始文件行号
    message: str                  # 警告内容


# ============================================================
# 自定义异常
# ============================================================


class Feishu2MdError(Exception):
    """所有模块异常的基类"""
    pass


class InputError(Feishu2MdError):
    """输入相关错误（文件不存在、格式不支持等）"""
    pass


class PandocNotFoundError(Feishu2MdError):
    """Pandoc 未安装"""
    pass


class PandocVersionError(Feishu2MdError):
    """Pandoc 版本过低"""
    pass


class WriteError(Feishu2MdError):
    """输出写入失败"""
    pass
