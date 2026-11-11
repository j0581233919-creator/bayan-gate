# Security & Privacy Policy

## Scope & Operational Context

`bayan-gate` is an Arabic/MENA-focused sensitive data recognition and privacy-safe redaction SDK and CLI designed to detect, classify, and redact regional personally identifiable information (PII) and sensitive financial/identity data with Arabic-Indic numeral normalization, exact character span tracking, zero sensitive logging, and strict fail-closed safety.

It is designed for execution within client applications, data ingestion pipelines, or ETL workflows. It is **not** an external network proxy or legally certified regulatory seal.

## Privacy & Security Guarantees

1. **Zero Sensitive Logging (Enforced by Default)**:
   - When serializing redaction results to dictionaries or JSON (`RedactionResult.to_dict()`), raw and normalized PII strings are strictly suppressed by default (`include_raw_spans=False`) and replaced with `[LENGTH_N]` placeholders. Raw sensitive values are never logged into system logs, error traces, or temporary audit stores.

2. **Zero Offset Drift across Mixed RTL/LTR Text**:
   - Redactions replace spans in descending order of character offsets (right to left), guaranteeing that preceding offsets remain 100% mathematically aligned regardless of differences in replacement string length.

3. **Tamper-Evident SHA-256 Audit Receipts**:
   - Every redaction operation computes a deterministic SHA-256 integrity hash over the input text, output text, and detected entities.

4. **Cryptographic Salt for Deterministic Pseudonymization**:
   - `PSEUDONYMIZE_HASH` generates keyed HMAC-SHA256 tokens using a caller-provided or session salt, preventing rainbow-table deanonymization.

5. **Pure Python Standard Library Runtime**:
   - Zero third-party PyPI dependencies, eliminating external package vulnerabilities or malicious dependencies.

## Reporting a Vulnerability

If you discover a privacy leak or security vulnerability in `bayan-gate`, please report it responsibly:
- Email: `security@localhost` (or contact maintainers via GitHub Security Advisories).
- Please include reproduction steps and sample text.
