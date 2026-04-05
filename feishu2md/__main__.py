"""CLI 入口 + 流水线编排。唯一的编排层，不包含任何业务逻辑。"""

import argparse
import sys
from pathlib import Path

from feishu2md.models import (
    InputError,
    PandocNotFoundError,
    PandocVersionError,
    Warning,
    WriteError,
)
from feishu2md import preprocessor, scanner, stripper, numbering, pandoc, writer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="feishu2md",
        description="Convert Feishu (飞书/Lark) docs to clean Markdown with auto-numbered headings.",
    )
    parser.add_argument(
        "input",
        type=str,
        help="Input file path (.md or .docx)",
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Output file path (default: stdout)",
    )
    parser.add_argument(
        "--inplace",
        action="store_true",
        default=False,
        help="Overwrite the input file (creates .bak backup by default)",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        default=False,
        help="Used with --inplace, skip creating .bak backup",
    )
    parser.add_argument(
        "--max-level",
        type=int,
        default=4,
        choices=range(1, 7),
        metavar="{1-6}",
        help="Max heading level to number (1-6, default: 4)",
    )
    parser.add_argument(
        "--strip-only",
        action="store_true",
        default=False,
        help="Only strip existing numbering, do not re-generate",
    )
    parser.add_argument(
        "--no-strip",
        action="store_true",
        default=False,
        help="Skip all stripping, add numbering directly",
    )
    parser.add_argument(
        "--force-strip",
        action="store_true",
        default=False,
        help="Force strip all suspected numbering (skip context validation)",
    )
    return parser


def validate_args(args: argparse.Namespace) -> None:
    """Validate CLI arguments. Raises InputError on failure."""
    # Mutually exclusive strip options
    count = sum([args.strip_only, args.no_strip, args.force_strip])
    if count > 1:
        raise InputError(
            "--strip-only, --no-strip, and --force-strip are mutually exclusive"
        )

    # Input file validation
    input_path = Path(args.input)
    if not input_path.exists():
        raise InputError(f"file not found: {input_path}")

    suffix = input_path.suffix.lower()
    if suffix not in (".md", ".docx"):
        raise InputError(
            f"unsupported file type '{suffix}', expected .md or .docx"
        )


def get_strip_mode(args: argparse.Namespace) -> str:
    """Derive strip mode string from CLI flags."""
    if args.strip_only:
        return "strip_only"
    if args.no_strip:
        return "none"
    if args.force_strip:
        return "force"
    return "auto"


def run_pipeline(args: argparse.Namespace) -> None:
    """Execute the processing pipeline. All exceptions propagate to main()."""
    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else None
    strip_mode = get_strip_mode(args)
    all_warnings: list[Warning] = []

    # 1. Input parsing
    if input_path.suffix.lower() == ".docx":
        output_dir = output_path.parent if output_path else input_path.parent
        content = pandoc.convert(input_path, output_dir=output_dir)
    else:
        content = input_path.read_text(encoding="utf-8")

    # 2. Preprocessing
    lines = preprocessor.preprocess(content)

    # 3. Heading scan
    scan_result, scan_warnings = scanner.scan(lines)
    all_warnings.extend(scan_warnings)

    # 4. Numbering strip
    lines, scan_result, strip_warnings = stripper.strip(
        lines, scan_result, mode=strip_mode
    )
    all_warnings.extend(strip_warnings)

    # 5. Numbering generation
    if strip_mode != "strip_only":
        lines, num_warnings = numbering.generate(
            lines, scan_result, max_level=args.max_level
        )
        all_warnings.extend(num_warnings)

    # 5b. No headings warning
    if not scan_result.headings:
        all_warnings.append(Warning(line_number=0, message="no headings found"))

    # 6. Output warnings
    for w in all_warnings:
        if w.message.startswith("number prefixes detected"):
            print(f"Info: {w.message}", file=sys.stderr)
        else:
            print(f"Warning: {w.message}", file=sys.stderr)

    # 7. Write output
    writer.write(
        lines,
        output=output_path,
        inplace=args.inplace,
        backup=not args.no_backup,
        input_path=input_path,
    )


def main(argv: list[str] | None = None) -> None:
    sys.stdout.reconfigure(encoding="utf-8")

    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        validate_args(args)
        run_pipeline(args)
    except InputError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except (PandocNotFoundError, PandocVersionError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)
    except WriteError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
