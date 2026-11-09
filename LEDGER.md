# BayanGate Task Ledger

## Current Context
- **Current Task**: BG-001 - Establish regional PII token models and Arabic-Indic normalization engine.
- **Current Owner**: Unassigned (Scheduled after QuoteJudge).
- **Branch**: main
- **Last Verified Commit**: None (Initial repository establishment)
- **Independent Review Status**: Not Started

## Backlog
| Task ID | Description | State | Owner | Acceptance Criteria |
|---------|-------------|-------|-------|---------------------|
| BG-001  | Arabic-Indic Numeral Normalizer & Span Mapper | READY | Pending | Bidirectional digit translation maintaining precise unicode string indices. |
| BG-002  | Regional Pattern Matchers (National IDs, GCC IBANs, Phones) | READY | Pending | Regex and algorithmic validation (Luhn for cards, mod-97 for IBANs, regional structure for IDs). |
| BG-003  | Redactor Engine & Masking Policies | READY | Pending | Configurable redaction (full `[REDACTED_...]`, partial masking, hash-based tokenization). Zero PII leakage in debug output. |
| BG-004  | CLI & Python SDK API | READY | Pending | Streaming redaction for files/STDOUT with zero-leak guarantee. |
| BG-005  | Synthetic Accuracy & Boundary Test Suite | READY | Pending | Comprehensive unit and property-based test cases covering tricky RTL/LTR mixing. |

## Limitations & Notes
- Checksums strictly verified where standard (Luhn, ISO 7064 MOD 97-10 for IBAN); no fictional algorithmic claims made.
- EGM plugin status: not yet installed in host AGY CLI; will integrate fresh-context goldfish review upon installation approval.
