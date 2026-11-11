# Verification & Quality Assurance Runbook

## Automated Test Execution

BayanGate maintains a 100% automated test suite using Python's standard `unittest` framework:

```bash
# Execute entire test suite
python3 -m unittest discover tests -v
```

### Test Suite Structure
- `tests/test_models.py`: Core data models, validation guards, exact grounding, and serialization.
- `tests/test_normalizer.py`: Arabic-Indic numeral translation, Tashkeel/Tatweel stripping, and zero-drift coordinate tracking.
- `tests/test_matchers.py`: Algorithmic validators (Luhn, ISO 7064 MOD 97-10 IBAN, Emirates ID, Egyptian ID, cards, phones).
- `tests/test_engine.py`: Regional PII engine multi-entity detection and deterministic overlap resolution.
- `tests/test_redactor.py`: Redactor engine, all 4 masking policies, reverse replacement, and HMAC tokenization.
- `tests/test_cli.py`: Subcommands (`redact`, `scan`, `demo`), streaming I/O, and CI/CD exit codes (0, 1, 3).
- `tests/test_synthetic_boundary.py`: Complex synthetic bilingual KYC agreements, diacritics/kashida stress, clinging punctuation, malformed candidates, and large corpus throughput.

## Verification Gate Checklist
1. All 117 unit and regression tests pass with 0 failures and 0 errors.
2. CLI subcommands (`bayan-gate --help`, `bayan-gate scan`, `bayan-gate redact`, `bayan-gate demo`) execute cleanly.
3. Clean installation via `pip install .` in isolated virtual environment executes successfully without network access.
