# BayanGate (بيان جيت)

> Arabic & MENA-focused sensitive data recognition and privacy-safe redaction SDK.

BayanGate provides high-precision recognition, classification, and redaction of Middle East & North Africa (MENA) regional Personally Identifiable Information (PII), national identification numbers, financial identifiers, contact records, and sensitive credentials with seamless Eastern Arabic-Indic numeral normalization (`٠-٩`), zero-drift unicode span tracking, and strict privacy-safe logging guarantees.

---

## Core Capabilities

- **Bidirectional Arabic-Indic Numeral Normalization**: Seamlessly translates Eastern Arabic-Indic numerals (`٠١٢٣٤٥٦٧٨٩`) and Extended Persian/Urdu numerals (`۰۱۲۳۴۵۶۷۸۹`) to Western ASCII digits (`0-9`) and vice versa.
- **Zero-Drift Unicode Span Mapping (`NormalizedText`)**: When stripping Arabic diacritics (Tashkeel / Harakat: Fatha, Damma, Kasra, Shadda, Sukun) or typographical elongations (Tatweel / Kashida `ـ`), BayanGate maintains exact character-by-character coordinate index maps. Detections found in normalized text map back to the raw source text with 100% exact character offset grounding (`[orig_start:orig_end]`).
- **Regional Entity Coverage (MENA Prioritized)**:
  - Saudi National ID (10 digits starting with `1`) & Iqama (10 digits starting with `2`)
  - UAE Resident Identity / Emirates ID (15 digits, `784-YYYY-XXXXXXX-Z`)
  - Egyptian National ID (14 digits)
  - GCC & Regional IBANs (Saudi `SA`, UAE `AE`, Kuwait `KW`, Qatar `QA`, Bahrain `BH`, Oman `OM`, Egypt `EG`)
  - Regional Phone Numbers (+966, +971, +20, etc.)
  - Credit / Debit Cards (with Luhn validation)
  - Emails, IP Addresses, and Custom Patterns
- **Configurable Redaction & Masking Policies (`PIIRedactor`)**:
  - `REDACT_FULL`: Replaces sensitive entities with category tags (`[REDACTED_SAUDI_NATIONAL_ID]`, `[REDACTED_GCC_IBAN]`).
  - `MASK_PARTIAL`: Format-preserving obfuscation retaining leading/trailing characters and delimiters (`108****678`, `SA03 **** **** 7519`, `١٠٨****٦٧٨`).
  - `PSEUDONYMIZE_HASH`: Salted deterministic HMAC surrogate tokenization (`[SA_ID_ab21e32b]`), ensuring consistent anonymization of recurring entities.
  - `REPLACE_SYNTHETIC`: Realistic synthetic dummy replacements.
- **Zero Offset Corruption**: Replaces character spans in reverse order (right to left) to eliminate coordinate drift across mixed RTL/LTR Arabic and Latin text.
- **Zero Sensitive Logging**: Audit records and diagnostic outputs redact raw unredacted PII by default to prevent accidental data leakage into log management systems.
- **Zero External Python Dependencies**: 100% pure Python standard library runtime (Python 3.10+).

---

## Quickstart

### 1. Run Automated Behavioral Tests (75 Passing Tests)
```bash
python3 -m unittest discover tests
```

### 2. Run the BG-001 Normalizer & Span Mapper Demonstration
```bash
python3 examples/run_normalizer_demo.py
```

### 3. Run the BG-002 Regional Pattern Matchers Demonstration
```bash
python3 examples/run_pattern_matching_demo.py
```

### 4. Run the BG-003 Redactor Engine Demonstration
```bash
python3 examples/run_redaction_demo.py
```

---

## Architecture & Governance

Refer to [AGENTS.md](AGENTS.md) and [LEDGER.md](LEDGER.md) for architectural guardrails, milestone roadmaps, and execution receipts.
