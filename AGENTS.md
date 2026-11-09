# AGENTS.md — BayanGate

## Authority & Mission
BayanGate is an Arabic/MENA-focused sensitive data recognition and redaction SDK/CLI designed to detect, classify, and redact regional personally identifiable information (PII) and sensitive financial/identity data with high fidelity, Arabic-Indic numeral normalization, exact character span tracking, zero sensitive logging, and strict fail-closed safety.

## Core Rules & Guardrails
1. **Numeral Normalization**: Seamlessly handle both Western Arabic (`0-9`) and Eastern Arabic-Indic numerals (`٠-٩`) across all pattern matching and span calculations without shifting offsets.
2. **Regional Identifier Coverage**: High-precision recognition for Saudi National ID/Iqama, UAE Resident Identity, Egyptian National ID, GCC IBANs, phone numbers with regional country codes (+966, +971, +20, etc.), credit card numbers, and emails.
3. **Exact Redaction & Span Offsets**: Return byte/character offsets for every detection, allowing both full masking, partial pseudonymization, and safe replacement without corrupting surrounding RTL Arabic text.
4. **No Sensitive Logging**: Absolute prohibition on logging raw unredacted PII in logs, error traces, or temporary audit stores.
5. **Fail-Closed Verification**: When an identifier is suspected or ambiguous, mark it for quarantine/review rather than leaking raw data. Never invent fictitious checksum algorithms or claim legally certified regulatory compliance.
6. **Independence**: Flash must not certify its own implementation as independently reviewed. Codex or independent reviewer certifies review status.

## Lifecycle States
`READY` -> `IN_PROGRESS` -> `IMPLEMENTED` -> `TESTED` -> `REVIEW_PENDING` -> `ACCEPTED` -> `RELEASE_READY`
