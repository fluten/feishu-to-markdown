#!/usr/bin/env python3
"""feishu-to-markdown: Convert Feishu/Lark docs to Markdown with auto-numbered headings."""

import argparse
import sys
from pathlib import Path


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
        default=3,
        choices=range(1, 7),
        metavar="{1-6}",
        help="Max heading level to number (1-6, default: 3)",
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


def validate_input(path: Path) -> None:
    """Validate input file exists and has a supported extension."""
    if not path.exists():
        print(f"Error: file not found: {path}", file=sys.stderr)
        sys.exit(1)

    suffix = path.suffix.lower()
    if suffix not in (".md", ".docx"):
        print(
            f"Error: unsupported file type '{suffix}', expected .md or .docx",
            file=sys.stderr,
        )
        sys.exit(1)


def validate_strip_args(args: argparse.Namespace) -> None:
    """Validate --strip-only, --no-strip, --force-strip are mutually exclusive."""
    count = sum([args.strip_only, args.no_strip, args.force_strip])
    if count > 1:
        print(
            "Error: --strip-only, --no-strip, and --force-strip are mutually exclusive",
            file=sys.stderr,
        )
        sys.exit(1)


def main(argv: list[str] | None = None) -> None:
    sys.stdout.reconfigure(encoding="utf-8")

    parser = build_parser()
    args = parser.parse_args(argv)

    # Validate mutually exclusive strip options (manual check for SPEC-compliant
    # error message and exit code 1)
    validate_strip_args(args)

    input_path = Path(args.input)
    validate_input(input_path)

    # .docx requires Pandoc (Phase 7); for now, exit early with clear message
    if input_path.suffix.lower() == ".docx":
        print(
            "Error: pandoc is required for .docx input. Install: https://pandoc.org/installing.html",
            file=sys.stderr,
        )
        sys.exit(2)

    # Read input
    content = input_path.read_text(encoding="utf-8")
    content = content.replace("\r\n", "\n")

    # Output
    if args.inplace:
        # Atomic write: tmp → bak → rename → delete bak (if --no-backup)
        tmp_path = input_path.with_suffix(input_path.suffix + ".tmp")
        bak_path = input_path.with_suffix(".md.bak")
        tmp_path.write_text(content, encoding="utf-8", newline="\n")
        input_path.rename(bak_path)
        tmp_path.rename(input_path)
        if args.no_backup:
            bak_path.unlink()
    elif args.output:
        output_path = Path(args.output)
        output_path.write_text(content, encoding="utf-8", newline="\n")
    else:
        sys.stdout.write(content)


if __name__ == "__main__":
    main()
