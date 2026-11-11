# Installation & Operator Guide — BayanGate (بيان جيت)

> **BayanGate**: Arabic & MENA-Focused Sensitive Data Recognition & Privacy-Safe Redaction SDK

---

## 1. System Requirements

- **Operating System**: Linux (recommended: Ubuntu/Debian, Pop!_OS, RHEL), macOS, or Windows (WSL recommended).
- **Python Runtime**: Python 3.10, 3.11, or 3.12.
- **Third-Party PyPI Dependencies**: **None (Zero external dependencies)**. BayanGate operates 100% on the Python standard library.

---

## 2. Installation

### Option A: Editable Developer Install (Recommended)
```bash
cd "bayan-gate/repo"
pip install -e .
```
This registers the CLI executable `bayan-gate` in your Python environment's binary path.

### Option B: Direct Python Module Invocation (No pip install required)
BayanGate can be run immediately without installation:
```bash
cd "bayan-gate/repo"
python3 -m bayan_gate.cli --help
```

---

## 3. CLI Command Reference

BayanGate provides three primary subcommands:

### 3.1 `redact` — Sensitive Data Redaction
Redacts personally identifiable information (PII) from an input file or standard input stream.

```bash
# 1. Full Redaction (Category Tags)
bayan-gate redact -i document.txt -o document_redacted.txt --policy full

# 2. Partial Masking (Preserves format and delimiters)
bayan-gate redact -i document.txt -o document_masked.txt --policy partial

# 3. Deterministic Pseudonymization (Keyed HMAC tokens)
bayan-gate redact -i document.txt --policy hash --salt "MySecretSalt"

# 4. Shell Pipe / Streaming Integration
cat raw_logs.txt | bayan-gate redact --policy full > sanitized_logs.txt

# 5. Generate Privacy-Safe JSON Audit Log
bayan-gate redact -i document.txt -o redacted.txt --audit-log audit_receipt.json
```

**Parameters**:
- `-i, --input`: Path to input file (or `-` for stdin).
- `-o, --output`: Path to output file (or `-` for stdout).
- `-p, --policy`: `full` (default), `partial`, `hash`, `synthetic`.
- `--salt`: Secret salt string for deterministic pseudonymization.
- `--mask-char`: Masking character for partial obfuscation (default: `*`).
- `--types`: Comma-separated list of entities to redact (e.g. `SAUDI_NATIONAL_ID,GCC_IBAN`).
- `--min-confidence`: Confidence threshold (default: `0.5`).
- `--audit-log`: Path to write cryptographic tamper-evident JSON audit receipt.
- `-q, --quiet`: Suppress diagnostic messages to `stderr`.

---

### 3.2 `scan` — Non-Destructive Sensitive Data Audit
Audits a document or standard input without modifying text. Designed for pre-commit hooks, CI/CD code scanning, and data leakage inspection.

```bash
# Human-readable audit report
bayan-gate scan -i confidential_doc.txt

# Machine-readable JSON summary for CI/CD gates
bayan-gate scan -i confidential_doc.txt --json
```

**Exit Codes**:
- `0`: Scan complete; **zero sensitive entities detected** (clean document).
- `1`: File not found or read error.
- `3`: **Sensitive entities detected** (triggers build failure in CI/CD pipelines or pre-commit hooks).

---

### 3.3 `demo` — Self-Contained Walkthrough
Runs an automated demonstration showcasing Arabic-Indic numeral translation, all 4 redaction policies, duplicate pseudonym consistency, and privacy-safe audit logging:

```bash
bayan-gate demo
```

---

## 4. Python SDK Usage

BayanGate provides top-level convenience functions for embedding directly into Python microservices, web apps, and data pipelines:

```python
import bayan_gate
from bayan_gate import EntityType, MaskingPolicy

# 1. Direct Detection
text = "رقم الهوية: ١٠٨٢٣٤٥٦٧٨ والآيبان: SA03 8000 0000 6080 1016 7519"
spans = bayan_gate.detect(text)
for span in spans:
    print(f"Detected {span.entity_type.value} at [{span.start_char}:{span.end_char}]: {span.raw_text}")

# 2. Direct Redaction
res = bayan_gate.redact(text, policy=MaskingPolicy.REDACT_FULL)
print(res.redacted_text)
# Output: "رقم الهوية: [REDACTED_SAUDI_NATIONAL_ID] والآيبان: [REDACTED_GCC_IBAN]"

# 3. Partial Masking
res_part = bayan_gate.redact(text, policy=MaskingPolicy.MASK_PARTIAL)
print(res_part.redacted_text)
# Output: "رقم الهوية: ١٠٨****٦٧٨ والآيبان: SA03 **** **** **** **** 7519"

# 4. Streaming Redaction (stdin -> stdout or file -> file)
with open("input.txt", "r", encoding="utf-8") as in_f, open("output.txt", "w", encoding="utf-8") as out_f:
    bayan_gate.stream_redact(in_f, out_f, policy=MaskingPolicy.REDACT_FULL)
```

---

## 5. Security & Privacy Guarantees

1. **Zero Sensitive Logging**:
   Serializing redaction results with `res.to_dict()` suppresses raw unredacted entity strings by default (`include_raw_spans=False`). Raw PII values are never emitted to application logs.

2. **Zero Offset Corruption**:
   Character replacements execute in reverse order (right to left) to prevent coordinate drift across mixed RTL/LTR Arabic and Latin text.

3. **Tamper-Evident SHA-256 Audit Digest**:
   Every redaction operation computes a cryptographic SHA-256 hash coupling input text, redacted output, and entity count.

---

## 6. Verification & Automated Tests

Run the full automated test suite (all 91 tests) anytime:
```bash
python3 -m unittest discover tests
```
