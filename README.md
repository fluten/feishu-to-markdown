# feishu-to-markdown [![](https://img.shields.io/badge/Python-3.10+-3776ab?logo=python&logoColor=white)](https://python.org) [![](https://img.shields.io/badge/License-MIT-green)](./LICENSE)

[![Feishu](https://img.shields.io/badge/Feishu-飞书-4285f4?logo=bytedance&logoColor=white)](https://www.feishu.cn) [![Lark](https://img.shields.io/badge/Lark-Docs-4285f4?logo=bytedance&logoColor=white)](https://www.larksuite.com) [![Pandoc](https://img.shields.io/badge/Pandoc-Optional-lightgrey?logo=pandoc)](https://pandoc.org) [![Markdown](https://img.shields.io/badge/Markdown-ATX_Headings-000?logo=markdown)](https://commonmark.org)

**English** | [简体中文](#简体中文)

Convert Feishu (飞书/Lark) exported documents to clean Markdown with auto-numbered headings. Solves the problem where Feishu's heading numbers are lost after exporting to `.docx` and converting to Markdown.

## Quick Start

```bash
# Process a .md file (from Pandoc conversion)
python -m feishu2md input.md -o output.md

# Process a .docx file directly (requires Pandoc)
python -m feishu2md input.docx -o output.md
```

**Before** (Pandoc output from Feishu .docx):

```markdown
1\. **产品概述**
2\. **功能设计**
2.1 **交互逻辑**
2.2 **视觉规范**
3\. **技术方案**
```

**After** (feishu-to-markdown output):

```markdown
## 1 产品概述
## 2 功能设计
### 2.1 交互逻辑
### 2.2 视觉规范
## 3 技术方案
```

## Features

- **Feishu Bold Heading Detection** — Automatically recognizes Feishu's `N\. **bold text**` pattern and converts to proper ATX headings (`#` / `##` / `###`)
- **Smart Numbering Strip** — Context-aware: strips Feishu auto-numbers while protecting version titles like `1.0 Overview` and `2024 Summary`
- **Auto Heading Numbering** — Generates hierarchical numbers (1 / 1.1 / 1.1.1) based on heading levels
- **Level Offset** — Documents starting from H2/H3 get numbering from `1` (not `0.1`)
- **Level Jump Handling** — H1 → H3 gaps auto-fill intermediate counters with `1`
- **Protected Regions** — Code blocks, HTML comments, front matter, and blockquotes are never touched
- **Setext → ATX** — Auto-converts `===` / `---` underline headings to `#` / `##`
- **GFM Table Output** — `.docx` tables converted to clean pipe format via GitHub Flavored Markdown
- **Idempotent** — Running twice produces identical output
- **Cross-platform** — Windows, macOS, Linux. UTF-8 everywhere, LF line endings

## Usage

```bash
# Output to stdout
python -m feishu2md input.md

# Output to file
python -m feishu2md input.md -o output.md

# Overwrite in-place (creates .bak backup)
python -m feishu2md input.md --inplace

# Overwrite without backup
python -m feishu2md input.md --inplace --no-backup

# Set max heading level for numbering (default: 3)
python -m feishu2md input.md --max-level 4

# Strip existing numbers only (no re-numbering)
python -m feishu2md input.md --strip-only

# Skip stripping, add numbers directly
python -m feishu2md input.md --no-strip

# Force strip all number-like prefixes
python -m feishu2md input.md --force-strip
```

### Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `input` | Input file path (`.md` or `.docx`) | required |
| `-o, --output` | Output file path | stdout |
| `--inplace` | Overwrite input file (creates `.bak`) | false |
| `--no-backup` | Skip `.bak` when using `--inplace` | false |
| `--max-level` | Max heading level to number (1–6) | 3 |
| `--strip-only` | Only strip numbers, don't re-generate | false |
| `--no-strip` | Skip stripping, add numbers directly | false |
| `--force-strip` | Force strip all suspected numbers | false |

> `--strip-only`, `--no-strip`, and `--force-strip` are mutually exclusive.

## How It Works

```
Feishu Document
  ↓ Export as .docx
  ↓ Pandoc converts to .md (or built-in via python -m feishu2md input.docx)
  ↓ feishu-to-markdown post-processing pipeline:
  │
  ├─ 1. Preprocess    → Normalize newlines, mark protected regions,
  │                      detect Feishu bold headings, convert Setext→ATX
  ├─ 2. Scan          → Identify headings, extract suspected numbers,
  │                      validate numbering sequence
  ├─ 3. Strip         → Smart strip (auto/force/none) existing numbers
  ├─ 4. Number        → Generate hierarchical numbers with level offsets
  └─ 5. Write         → Output to stdout / file / in-place
  ↓
Clean .md with auto-numbered headings
```

## Smart Stripping

The tool distinguishes Feishu auto-numbers from real content:

| Input | Detected As | Action |
|-------|-------------|--------|
| `# 1 产品概述` / `## 1.1 功能设计` | Valid sequence → Feishu numbering | Strip & re-number |
| `# 1.0 概述` / `## 2.0 Release Notes` | Invalid sequence → version titles | **Preserved** |
| `# 2024 年度总结` / `## 3D 建模` | Not a number pattern | **Preserved** |
| `# 一、概述` / `## （一）设计` | Chinese numbering | Always stripped |

## Project Structure

```
feishu-to-markdown/
├── feishu2md/
│   ├── __init__.py        # Package init, version
│   ├── __main__.py        # CLI entry + pipeline orchestration
│   ├── models.py          # Shared dataclasses + exceptions
│   ├── preprocessor.py    # Newlines, protected regions, Feishu bold headings, Setext
│   ├── scanner.py         # Heading identification, number extraction, sequence validation
│   ├── stripper.py        # Smart number stripping (auto/force/none/strip-only)
│   ├── numbering.py       # Hierarchical number generation
│   ├── pandoc.py          # Pandoc version detection + .docx conversion
│   └── writer.py          # stdout / file / in-place atomic write
├── tests/                 # 398 tests (pytest)
├── pyproject.toml
├── LICENSE
└── README.md
```

## Installation

**Requirements:** Python 3.10+ (no third-party dependencies)

```bash
git clone https://github.com/fluten/feishu-to-markdown.git
cd feishu-to-markdown
```

For `.docx` input, [Pandoc](https://pandoc.org/installing.html) is also needed:

```bash
# macOS
brew install pandoc

# Windows
winget install JohnMacFarlane.Pandoc

# Ubuntu/Debian
sudo apt install pandoc
```

## Testing

```bash
# Run all tests
python -m pytest tests/

# Skip Pandoc integration tests
python -m pytest tests/ -m "not integration"
```

## License

[MIT](./LICENSE)

---

<a id="简体中文"></a>

# feishu-to-markdown [![](https://img.shields.io/badge/Python-3.10+-3776ab?logo=python&logoColor=white)](https://python.org) [![](https://img.shields.io/badge/License-MIT-green)](./LICENSE)

[![飞书](https://img.shields.io/badge/飞书-Feishu-4285f4?logo=bytedance&logoColor=white)](https://www.feishu.cn) [![Pandoc](https://img.shields.io/badge/Pandoc-可选-lightgrey?logo=pandoc)](https://pandoc.org) [![Markdown](https://img.shields.io/badge/Markdown-标题编号-000?logo=markdown)](https://commonmark.org)

飞书文档导出 Markdown 标题自动编号工具。解决飞书文档导出为 `.docx` 再转 Markdown 后，标题编号丢失的问题。

## 快速开始

```bash
# 处理 .md 文件
python -m feishu2md input.md -o output.md

# 直接处理飞书导出的 .docx（需要 Pandoc）
python -m feishu2md input.docx -o output.md
```

**转换前**（Pandoc 从飞书 .docx 转出的 Markdown）：

```markdown
1\. **产品概述**
2\. **功能设计**
2.1 **交互逻辑**
2.2 **视觉规范**
3\. **技术方案**
```

**转换后**：

```markdown
## 1 产品概述
## 2 功能设计
### 2.1 交互逻辑
### 2.2 视觉规范
## 3 技术方案
```

## 功能特性

- **飞书粗体标题识别** — 自动识别飞书特有的 `N\. **粗体文本**` 格式，转换为标准 ATX 标题
- **智能编号剥离** — 基于上下文校验，剥离飞书自动编号，同时保护版本号标题（如 `1.0 概述`、`2024 年度总结`）
- **自动标题编号** — 按层级生成 1 / 1.1 / 1.1.1 格式的编号
- **层级偏移** — 文档从 H2/H3 开头时，编号从 `1` 开始（不会出现 `0.1`）
- **层级跳跃补全** — H1 直接跳 H3 时，自动补充中间层级
- **受保护区域** — 代码块、HTML 注释、front matter、blockquote 内的内容不受影响
- **Setext 标题转换** — 自动将 `===` / `---` 下划线标题转为 `#` / `##` 格式
- **GFM 表格输出** — `.docx` 中的表格转为 GitHub 风格 Markdown 表格
- **幂等输出** — 对输出再次运行，结果完全一致
- **跨平台** — Windows、macOS、Linux，统一 UTF-8 编码和 LF 换行

## 安装

**依赖：** Python 3.10+（无第三方依赖）

```bash
git clone https://github.com/fluten/feishu-to-markdown.git
cd feishu-to-markdown
```

处理 `.docx` 文件需要安装 [Pandoc](https://pandoc.org/installing.html)：

```bash
# macOS
brew install pandoc

# Windows
winget install JohnMacFarlane.Pandoc

# Ubuntu/Debian
sudo apt install pandoc
```

## 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `input` | 输入文件路径（`.md` 或 `.docx`） | 必填 |
| `-o, --output` | 输出文件路径 | stdout |
| `--inplace` | 覆盖原文件（自动生成 `.bak` 备份） | false |
| `--no-backup` | 与 `--inplace` 配合，跳过备份 | false |
| `--max-level` | 参与编号的最大标题层级（1–6） | 3 |
| `--strip-only` | 仅剥离已有编号，不重新生成 | false |
| `--no-strip` | 跳过编号剥离，直接添加编号 | false |
| `--force-strip` | 强制剥离所有疑似编号 | false |

> `--strip-only`、`--no-strip`、`--force-strip` 三者互斥。

## 许可证

[MIT](./LICENSE)
