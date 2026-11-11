"""Command Line Interface for BayanGate.

Provides:
- redact: Detects and redacts sensitive PII from files or standard input streaming.
- scan: Audits and reports detected sensitive entities without modifying text (useful for CI/CD gates).
- demo: Runs an interactive demonstration of all 4 masking policies.
"""

from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional, Set, TextIO

from .models import EntityType, MaskingPolicy, RedactionResult
from .engine import RegionalPIIEngine
from .redactor import PIIRedactor


def parse_types_arg(types_str: Optional[str]) -> Optional[Set[EntityType]]:
    """Parses comma-separated entity types."""
    if not types_str or not types_str.strip():
        return None

    types: Set[EntityType] = set()
    parts = types_str.split(",")
    for part in parts:
        clean = part.strip().upper()
        if not clean:
            continue
        try:
            types.add(EntityType(clean))
        except ValueError:
            valid_names = [e.value for e in EntityType]
            raise ValueError(
                f"Unknown entity type '{part.strip()}'. Valid types are: {', '.join(valid_names)}"
            )

    return types if types else None


def cmd_redact(args: argparse.Namespace) -> int:
    """Redacts sensitive PII from a file or standard input."""
    policy_map = {
        "full": MaskingPolicy.REDACT_FULL,
        "partial": MaskingPolicy.MASK_PARTIAL,
        "hash": MaskingPolicy.PSEUDONYMIZE_HASH,
        "synthetic": MaskingPolicy.REPLACE_SYNTHETIC,
    }
    policy = policy_map.get(args.policy.lower(), MaskingPolicy.REDACT_FULL)

    try:
        enabled_types = parse_types_arg(getattr(args, "types", None))
    except ValueError as e:
        print(f"Error parsing --types: {e}", file=sys.stderr)
        return 1

    redactor = PIIRedactor(
        salt=getattr(args, "salt", None),
        mask_char=getattr(args, "mask_char", "*"),
    )

    # Read input from file or stdin
    in_file = getattr(args, "input", None)
    if not in_file or in_file == "-":
        input_text = sys.stdin.read()
    else:
        in_path = Path(in_file)
        if not in_path.exists():
            print(f"Error: Input file '{in_file}' not found.", file=sys.stderr)
            return 1
        try:
            input_text = in_path.read_text(encoding="utf-8")
        except Exception as e:
            print(f"Error reading file '{in_file}': {e}", file=sys.stderr)
            return 1

    # Apply redaction
    result = redactor.redact(
        input_text,
        policy=policy,
        enabled_types=enabled_types,
        min_confidence=getattr(args, "min_confidence", None),
    )

    # Write output to file or stdout
    out_file = getattr(args, "output", None)
    if not out_file or out_file == "-":
        sys.stdout.write(result.redacted_text)
        if not result.redacted_text.endswith("\n"):
            sys.stdout.write("\n")
    else:
        out_path = Path(out_file)
        try:
            out_path.write_text(result.redacted_text, encoding="utf-8")
        except Exception as e:
            print(f"Error writing to output file '{out_file}': {e}", file=sys.stderr)
            return 1

    # Optional Audit Log
    audit_file = getattr(args, "audit_log", None)
    if audit_file:
        audit_path = Path(audit_file)
        try:
            safe_audit = result.to_dict(include_raw_spans=False)
            audit_path.write_text(json.dumps(safe_audit, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            print(f"Error writing audit log '{audit_file}': {e}", file=sys.stderr)
            return 1

    if not getattr(args, "quiet", False) and out_file and out_file != "-":
        print(f"Redaction complete: {result.redaction_count} entities redacted. Saved to '{out_file}'.", file=sys.stderr)

    return 0


def cmd_scan(args: argparse.Namespace) -> int:
    """Audits text and reports detected sensitive entities without modifying content."""
    try:
        enabled_types = parse_types_arg(getattr(args, "types", None))
    except ValueError as e:
        print(f"Error parsing --types: {e}", file=sys.stderr)
        return 1

    engine = RegionalPIIEngine()

    in_file = getattr(args, "input", None)
    if not in_file or in_file == "-":
        input_text = sys.stdin.read()
        source_label = "stdin"
    else:
        in_path = Path(in_file)
        if not in_path.exists():
            print(f"Error: Input file '{in_file}' not found.", file=sys.stderr)
            return 1
        try:
            input_text = in_path.read_text(encoding="utf-8")
            source_label = in_path.name
        except Exception as e:
            print(f"Error reading file '{in_file}': {e}", file=sys.stderr)
            return 1

    spans = engine.detect(
        input_text,
        enabled_types=enabled_types,
        min_confidence=getattr(args, "min_confidence", None),
    )

    if getattr(args, "json", False):
        summary = {
            "source": source_label,
            "detected_count": len(spans),
            "entity_type_counts": {},
            "findings": [s.to_dict() for s in spans],
        }
        for s in spans:
            k = s.entity_type.value
            summary["entity_type_counts"][k] = summary["entity_type_counts"].get(k, 0) + 1
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 3 if spans else 0

    print("=" * 65)
    print(f"BayanGate Sensitive Data Scan: {source_label}")
    print("=" * 65)
    if not spans:
        print("  ✅ Zero sensitive entities detected. Content is clean.")
        print("=" * 65)
        return 0

    print(f"  ⚠️  Detected {len(spans)} sensitive entity / entities:\n")
    for idx, s in enumerate(spans, 1):
        chk_str = ""
        if s.is_valid_checksum is not None:
            chk_str = f" | Checksum: {'PASS' if s.is_valid_checksum else 'FAIL'}"
        print(f"  {idx:2d}. [{s.entity_type.value}] at char [{s.start_char}:{s.end_char}] (Confidence: {s.confidence:.2f}{chk_str})")

    print("\n" + "=" * 65)
    return 3  # Exit code 3 signals PII detected (for pre-commit hooks / CI checks)


def cmd_demo(args: argparse.Namespace) -> int:
    """Runs the self-contained demonstration."""
    from .demo import run_demo
    return run_demo()


def build_parser() -> argparse.ArgumentParser:
    """Builds the BayanGate CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="bayan-gate",
        description="Arabic & MENA-focused sensitive data recognition and privacy-safe redaction SDK/CLI.",
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="BayanGate subcommands")

    # 1. redact
    p_red = subparsers.add_parser("redact", help="Detect and redact sensitive PII from files or standard input")
    p_red.add_argument("-i", "--input", help="Path to input text file (or '-' for stdin)")
    p_red.add_argument("-o", "--output", help="Path to save redacted output (or '-' for stdout)")
    p_red.add_argument(
        "-p", "--policy",
        choices=["full", "partial", "hash", "synthetic"],
        default="full",
        help="Redaction policy (default: full)",
    )
    p_red.add_argument("--salt", help="Secret salt string for deterministic pseudonymization (hash policy)")
    p_red.add_argument("--mask-char", default="*", help="Masking character for partial masking (default: '*')")
    p_red.add_argument("--types", help="Comma-separated entity types to redact (e.g. SAUDI_NATIONAL_ID,GCC_IBAN)")
    p_red.add_argument("--min-confidence", type=float, default=0.5, help="Minimum detection confidence (default: 0.5)")
    p_red.add_argument("--audit-log", help="Path to write privacy-safe JSON audit log")
    p_red.add_argument("-q", "--quiet", action="store_true", help="Suppress status messages on stderr")
    p_red.set_defaults(func=cmd_redact)

    # 2. scan
    p_scn = subparsers.add_parser("scan", help="Audit and detect sensitive PII without modifying text")
    p_scn.add_argument("-i", "--input", help="Path to input text file (or '-' for stdin)")
    p_scn.add_argument("--json", action="store_true", help="Output findings in structured JSON format")
    p_scn.add_argument("--types", help="Comma-separated entity types to inspect")
    p_scn.add_argument("--min-confidence", type=float, default=0.5, help="Minimum detection confidence")
    p_scn.set_defaults(func=cmd_scan)

    # 3. demo
    p_dmo = subparsers.add_parser("demo", help="Run interactive demonstration of redaction policies")
    p_dmo.set_defaults(func=cmd_demo)

    return parser


def main() -> int:
    """Main CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()

    if not hasattr(args, "func"):
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
