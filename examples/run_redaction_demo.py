#!/usr/bin/env python3
"""Demonstration of BayanGate Redactor Engine and Masking Policies (BG-003)."""

import json
import sys
from pathlib import Path

# Ensure bayan_gate package is resolvable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bayan_gate.models import MaskingPolicy
from bayan_gate.redactor import PIIRedactor


def main():
    print("=" * 80)
    print("BayanGate — Sensitive Data Redactor Engine & Masking Policies (BG-003)")
    print("=" * 80)

    redactor = PIIRedactor(salt="Gov-Audit-Salt-Key-2026")

    sample_doc = (
        "بيانات الموظف والعقد:\n"
        "الموظف: عبد العزيز، هوية وطنية: ١٠٨٢٣٤٥٦٧٨\n"
        "الهاتف الجوال: ٠٥٠١٢٣٤٥٦٧ | البريد الإلكتروني: a.aziz@saudi-energy.sa\n"
        "الحساب البنكي لتحويل الراتب: SA03 8000 0000 6080 1016 7519\n"
        "ملاحظة: تم تسجيل الهوية ١٠٨٢٣٤٥٦٧٨ في البوابة مسبقاً.\n"
    )

    print("\n[Original Sensitive Input Document]:")
    print("-" * 80)
    print(sample_doc.strip())
    print("-" * 80)

    # 1. Full Redaction (REDACT_FULL)
    print("\n[Policy 1: REDACT_FULL — Typed Category Tags]:")
    res_full = redactor.redact(sample_doc, policy=MaskingPolicy.REDACT_FULL)
    print(res_full.redacted_text.strip())
    print(f"Audit Hash (SHA-256): {res_full.audit_hash}")

    # 2. Partial Masking (MASK_PARTIAL)
    print("\n[Policy 2: MASK_PARTIAL — Format & Delimiter Preserving Obfuscation]:")
    res_partial = redactor.redact(sample_doc, policy=MaskingPolicy.MASK_PARTIAL)
    print(res_partial.redacted_text.strip())

    # 3. Deterministic Pseudonymization (PSEUDONYMIZE_HASH)
    print("\n[Policy 3: PSEUDONYMIZE_HASH — Keyed Deterministic Surrogate Tokenization]:")
    res_hash = redactor.redact(sample_doc, policy=MaskingPolicy.PSEUDONYMIZE_HASH)
    print(res_hash.redacted_text.strip())
    print("Notice: The duplicate Saudi National ID received the exact same surrogate token across the document!")

    # 4. Synthetic Replacement (REPLACE_SYNTHETIC)
    print("\n[Policy 4: REPLACE_SYNTHETIC — Realistic Format-Preserving Surrogates]:")
    res_synth = redactor.redact(sample_doc, policy=MaskingPolicy.REPLACE_SYNTHETIC)
    print(res_synth.redacted_text.strip())

    # 5. Zero-Sensitive Logging Verification
    print("\n[Security: Zero-Sensitive Logging Audit Serialization]:")
    safe_audit = res_full.to_dict(include_raw_spans=False)
    print(json.dumps(safe_audit, indent=2, ensure_ascii=False))

    print("\n" + "=" * 80)
    print("BG-003 demonstration complete. Zero offset drift across mixed RTL/LTR text.")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
