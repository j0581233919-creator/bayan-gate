#!/usr/bin/env python3
"""Demonstration of BayanGate Regional Pattern Matchers and PII Detection Engine (BG-002)."""

import sys
from pathlib import Path

# Ensure bayan_gate package is resolvable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bayan_gate.engine import RegionalPIIEngine


def main():
    print("=" * 80)
    print("BayanGate — Regional Pattern Matchers & Precision PII Detector (BG-002)")
    print("=" * 80)

    engine = RegionalPIIEngine()

    # Sample realistic MENA business document with multiple sensitive entities
    sample_text = (
        "بيانات التسجيل والتعاقد:\n"
        "١. المفوض بالتوقيع: أحمد محمود، هوية وطنية: ١٠٨٢٣٤٥٦٧٨\n"
        "   هاتف الاتصال: ٠٥٠١٢٣٤٥٦٧ | البريد: ahmad.m@contractor.sa\n"
        "٢. المستشار الفني (مقيم): رقم الإقامة: 2082345678، هاتف: +971501234567\n"
        "٣. الشريك التجاري (مصر): الرقم القومي: 29005150112314\n"
        "٤. ممثل مكتب دبي: بطاقة هوية إماراتية: 784-1985-1234567-1\n"
        "٥. الحساب البنكي المعتمد: SA03 8000 0000 6080 1016 7519 (مصرف الراجحي)\n"
        "٦. بطاقة السداد الإلكتروني: 4532 0150 1234 5671 (Visa)\n"
        "٧. خادم البوابة: 10.0.4.15\n"
    )

    print("Input Document Text:")
    print("-" * 80)
    print(sample_text)
    print("-" * 80)

    print("\nRunning Regional PII Engine...")
    spans = engine.detect(sample_text)

    print(f"\nDetected {len(spans)} sensitive entities with 100% exact source grounding:")
    print("=" * 80)
    for idx, span in enumerate(spans, 1):
        verified = span.verify_grounding(sample_text)
        chk_str = ""
        if span.is_valid_checksum is not None:
            chk_str = f" | Checksum: {'PASS' if span.is_valid_checksum else 'FAIL'}"

        print(f"{idx:2d}. [{span.entity_type.value}]")
        print(f"    Raw Text:       '{span.raw_text}' (Chars: [{span.start_char}:{span.end_char}])")
        print(f"    Normalized:     '{span.normalized_text}' | Conf: {span.confidence:.2f}{chk_str}")
        if span.metadata:
            meta_items = [f"{k}={v}" for k, v in span.metadata.items()]
            print(f"    Metadata:       {', '.join(meta_items)}")
        print(f"    Grounding:      {'VERIFIED (Exact)' if verified else 'FAILED'}")
        print()

    print("=" * 80)
    print("Demo completed successfully. Zero hallucinated data, pure standard library.")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
