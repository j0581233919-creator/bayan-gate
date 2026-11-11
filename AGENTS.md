# AGENTS.md — BayanGate

## Authority & Mission
BayanGate is an Arabic/MENA-focused sensitive data recognition and redaction SDK/CLI designed to detect, classify, and redact regional personally identifiable information (PII) and sensitive financial/identity data with high fidelity, Arabic-Indic numeral normalization, exact character span tracking, zero sensitive logging, and strict fail-closed safety.

## Core Rules & Guardrails
1. **Numeral Normalization**: Seamlessly handle both Western Arabic (`0-9`) and Eastern Arabic-Indic numerals (`٠-٩`) across all pattern matching and span calculations without shifting offsets.
2. **Regional Identifier Coverage**: High-precision recognition for Saudi National ID/Iqama, UAE Resident Identity, Egyptian National ID, GCC IBANs, phone numbers with regional country codes (+966, +971, +20, etc.), credit card numbers, and emails.
3. **Exact Redaction & Span Offsets**: Return byte/character offsets for every detection, allowing both full masking, partial pseudonymization, and safe replacement without corrupting surrounding RTL Arabic text.
4. **No Sensitive Logging**: Absolute prohibition on logging raw unredacted PII in logs, error traces, or temporary audit stores.
5. **Fail-Closed Verification**: When an identifier is suspected or ambiguous, mark it for quarantine/review rather than leaking raw data. Never invent fictitious checksum algorithms or claim legally certified regulatory compliance.
6. **Independent Review Requirement & Codex Exclusion Policy**:
   - OpenAI Codex CLI and API are **strictly disabled** for this development program (CatalogCopilot, QuoteJudge, BayanGate).
   - Never invoke Codex directly or indirectly (via CLI, AGY, Mezo, Hermes, MezoExecutor, EGM, or fallback loops).
   - Independent engineering review and certification are conducted via verified Google Elephant-Goldfish Model (EGM) Goldfish reviewers (`egm-codebase-details` and `egm-structural`) using genuine fresh-context subagents.
   - Flash/Executor agents must NOT certify their own implementation as independently reviewed.

## Lifecycle States
`READY` -> `IN_PROGRESS` -> `IMPLEMENTED` -> `TESTED` -> `REVIEW_PENDING` -> `ACCEPTED` -> `RELEASE_READY`

## Task Ledger Summary
- **Current Task**: BG-001 — Arabic-Indic Numeral Normalizer & Span Mapper.
- **Current Lifecycle State**: `REVIEW_PENDING`
- **Current Owner**: Gemini Flash (Lead Engineering Executor).
- **Independent Reviewer**: EGM Goldfish Codebase Details Auditor (`egm-codebase-details`).
- **Branch**: main
- **Last Verified Commit**: 110da37
- **Independent Review Status**: BG-001 implemented with 20/20 automated tests passing; submitted for independent EGM Goldfish review.

## Verification Criteria for BG-001
1. **Core Data Models (`bayan_gate/models.py`)**:
   - `EntityType` enum covering MENA regional documents (Saudi National ID/Iqama, Emirates ID, Egyptian National ID, GCC IBANs) and general identifiers (Phone, Credit Card, Email, etc.).
   - `MaskingPolicy` enum defining transformation modes (`REDACT_FULL`, `MASK_PARTIAL`, `PSEUDONYMIZE_HASH`, `REPLACE_SYNTHETIC`).
   - `PIISpan` dataclass with exact character offsets (`[start_char:end_char]`), validation guards, `verify_grounding(original_text)`, and dictionary serialization.
   - `RedactionResult` dataclass with privacy-safe default serialization (`include_raw_spans=False`).
2. **Arabic-Indic Numeral Normalizer & Span Mapper (`bayan_gate/normalizer.py`)**:
   - Bidirectional digit translation (`to_western_digits`, `to_arabic_indic_digits`) for Eastern Arabic-Indic (`٠-٩`) and Extended Persian/Urdu digits (`۰-۹`).
   - Zero-drift `NormalizedText` tracking `index_map` and `reverse_map` when stripping diacritics (Tashkeel) and Tatweel/Kashida (`ـ`).
   - `map_span_to_original(norm_start, norm_end)` mapping normalized spans to 100% exact original unicode text slices.
3. **Pure Standard Library Runtime**:
   - Zero external PyPI dependencies (`dependencies = []` in `pyproject.toml`).
4. **Automated Verification**:
   - Comprehensive test suite passing with 0 failures (`python3 -m unittest discover tests`).
   - Executable demonstration script in `examples/run_normalizer_demo.py`.
