"""Unit and integration tests for PIIRedactor and masking policies (BG-003)."""

import unittest
from bayan_gate.models import EntityType, MaskingPolicy, PIISpan
from bayan_gate.redactor import PIIRedactor


class TestPIIRedactor(unittest.TestCase):
    def setUp(self):
        self.redactor = PIIRedactor()

    # -------------------------------------------------------------
    # 1. Full Redaction Policy Tests (REDACT_FULL)
    # -------------------------------------------------------------
    def test_redact_full_basic(self):
        text = "رقم الهوية: 1082345678، الهاتف: 0501234567"
        res = self.redactor.redact(text, policy=MaskingPolicy.REDACT_FULL)

        self.assertEqual(res.redaction_count, 2)
        self.assertIn("[REDACTED_SAUDI_NATIONAL_ID]", res.redacted_text)
        self.assertIn("[REDACTED_PHONE_NUMBER]", res.redacted_text)
        self.assertNotIn("1082345678", res.redacted_text)
        self.assertNotIn("0501234567", res.redacted_text)

        # Audit hash is generated
        self.assertIsNotNone(res.audit_hash)
        self.assertEqual(len(res.audit_hash), 64)

    def test_redact_full_zero_sensitive_logging(self):
        text = "العميل: أحمد، الهوية: 1082345678، البريد: ahmed@example.com"
        res = self.redactor.redact(text, policy=MaskingPolicy.REDACT_FULL)

        # Default serialization suppresses raw values
        safe_dict = res.to_dict(include_raw_spans=False)
        safe_str = str(safe_dict)
        self.assertNotIn("1082345678", safe_str)
        self.assertNotIn("ahmed@example.com", safe_str)
        self.assertIn("[LENGTH_10]", safe_str)

    def test_redact_custom_replacer(self):
        text = "الهوية: 1082345678"
        res = self.redactor.redact(
            text,
            custom_replacer=lambda s: f"[{s.entity_type.name}_CONFIDENTIAL]"
        )
        self.assertEqual(res.redacted_text, "الهوية: [SAUDI_NATIONAL_ID_CONFIDENTIAL]")

    # -------------------------------------------------------------
    # 2. Partial Masking Policy Tests (MASK_PARTIAL)
    # -------------------------------------------------------------
    def test_mask_partial_saudi_national_id(self):
        # 10 digits: keep first 3 and last 3, mask middle 4
        text = "هوية المواطن: 1082345678"
        res = self.redactor.redact(text, policy=MaskingPolicy.MASK_PARTIAL)
        self.assertIn("108****678", res.redacted_text)

    def test_mask_partial_saudi_id_eastern_numerals(self):
        # Eastern Arabic-Indic numerals: ١٠٨٢٣٤٥٦٧٨
        text = "الهوية الوطنية: ١٠٨٢٣٤٥٦٧٨"
        res = self.redactor.redact(text, policy=MaskingPolicy.MASK_PARTIAL)
        self.assertIn("١٠٨****٦٧٨", res.redacted_text)

    def test_mask_partial_uae_emirates_id(self):
        text = "بطاقة الهوية: 784-1985-1234567-1"
        res = self.redactor.redact(text, policy=MaskingPolicy.MASK_PARTIAL)
        self.assertIn("784-****-*******-1", res.redacted_text)

    def test_mask_partial_egyptian_national_id(self):
        # 14 digits: keep first 3 and last 3, mask middle 8
        text = "الرقم القومي: 29005150112314"
        res = self.redactor.redact(text, policy=MaskingPolicy.MASK_PARTIAL)
        self.assertIn("290********314", res.redacted_text)

    def test_mask_partial_gcc_iban(self):
        # Keep SA03 and last 4, mask middle while preserving spaces
        text = "IBAN: SA03 8000 0000 6080 1016 7519"
        res = self.redactor.redact(text, policy=MaskingPolicy.MASK_PARTIAL)
        self.assertIn("SA03 **** **** **** **** 7519", res.redacted_text)

    def test_mask_partial_credit_card(self):
        text = "Card: 4532 0150 1234 5671"
        res = self.redactor.redact(text, policy=MaskingPolicy.MASK_PARTIAL)
        self.assertIn("4532 **** **** 5671", res.redacted_text)

    def test_mask_partial_email(self):
        text = "Contact: support@example.com, and tariq@gov.sa"
        res = self.redactor.redact(text, policy=MaskingPolicy.MASK_PARTIAL)
        self.assertIn("s*****t@example.com", res.redacted_text)
        self.assertIn("t***q@gov.sa", res.redacted_text)

    def test_mask_partial_ip_address(self):
        text = "Server: 192.168.1.100"
        res = self.redactor.redact(text, policy=MaskingPolicy.MASK_PARTIAL)
        self.assertIn("192.168.*.***", res.redacted_text)

    def test_mask_partial_custom_mask_char(self):
        custom_redactor = PIIRedactor(mask_char="X")
        text = "ID: 1082345678"
        res = custom_redactor.redact(text, policy=MaskingPolicy.MASK_PARTIAL)
        self.assertIn("108XXXX678", res.redacted_text)

    # -------------------------------------------------------------
    # 3. Deterministic Pseudonymization (PSEUDONYMIZE_HASH)
    # -------------------------------------------------------------
    def test_pseudonymize_hash_consistency(self):
        # Same ID appearing twice in a document receives the EXACT same surrogate token
        text = "المستخدم 1082345678 قام بالتسجيل. تم التحقق من 1082345678 بنجاح."
        res = self.redactor.redact(text, policy=MaskingPolicy.PSEUDONYMIZE_HASH)

        self.assertEqual(res.redaction_count, 2)
        # Extract tokens from redacted text
        tokens = [word for word in res.redacted_text.split() if word.startswith("[SA_ID_")]
        self.assertEqual(len(tokens), 2)
        # Both tokens must be identical!
        self.assertEqual(tokens[0], tokens[1])
        self.assertNotIn("1082345678", res.redacted_text)

    def test_pseudonymize_hash_different_entities_produce_different_tokens(self):
        text = "ID 1: 1082345678, ID 2: 2082345678"
        res = self.redactor.redact(text, policy=MaskingPolicy.PSEUDONYMIZE_HASH)

        self.assertEqual(res.redaction_count, 2)
        token1 = res.entities_detected[0]
        token2 = res.entities_detected[1]
        self.assertNotEqual(token1.normalized_text, token2.normalized_text)

    def test_pseudonymize_hash_salt_isolation(self):
        text = "ID: 1082345678"
        redactor1 = PIIRedactor(salt="Salt-Alpha")
        redactor2 = PIIRedactor(salt="Salt-Beta")

        res1 = redactor1.redact(text, policy=MaskingPolicy.PSEUDONYMIZE_HASH)
        res2 = redactor2.redact(text, policy=MaskingPolicy.PSEUDONYMIZE_HASH)

        self.assertNotEqual(res1.redacted_text, res2.redacted_text)

    # -------------------------------------------------------------
    # 4. Synthetic Replacement Policy (REPLACE_SYNTHETIC)
    # -------------------------------------------------------------
    def test_replace_synthetic(self):
        text = "Saudi ID: 1082345678, Email: user@domain.com, IBAN: SA0380000000608010167519"
        res = self.redactor.redact(text, policy=MaskingPolicy.REPLACE_SYNTHETIC)

        self.assertEqual(res.redaction_count, 3)
        self.assertIn("1999999999", res.redacted_text)
        self.assertIn("redacted-user@example.com", res.redacted_text)
        self.assertIn("SA0000000000000000000000", res.redacted_text)
        self.assertNotIn("1082345678", res.redacted_text)
        self.assertNotIn("user@domain.com", res.redacted_text)

    # -------------------------------------------------------------
    # 5. Reverse Replacement Invariance & RTL/LTR Safety
    # -------------------------------------------------------------
    def test_reverse_replacement_prevents_offset_drift(self):
        # 3 entities where each replacement changes the string length significantly
        text = "أولاً: 1082345678، ثانياً: 0501234567، ثالثاً: test@example.sa"
        res = self.redactor.redact(text, policy=MaskingPolicy.REDACT_FULL)

        self.assertEqual(res.redaction_count, 3)
        self.assertTrue(res.redacted_text.startswith("أولاً: [REDACTED_SAUDI_NATIONAL_ID]"))
        self.assertIn("ثانياً: [REDACTED_PHONE_NUMBER]", res.redacted_text)
        self.assertTrue(res.redacted_text.endswith("ثالثاً: [REDACTED_EMAIL_ADDRESS]"))

    def test_empty_string_redaction(self):
        res = self.redactor.redact("")
        self.assertEqual(res.redacted_text, "")
        self.assertEqual(res.redaction_count, 0)

    def test_audit_hash_deterministic(self):
        text = "Citizen ID: 1082345678"
        res1 = self.redactor.redact(text, policy=MaskingPolicy.REDACT_FULL)
        res2 = self.redactor.redact(text, policy=MaskingPolicy.REDACT_FULL)
        self.assertEqual(res1.audit_hash, res2.audit_hash)


if __name__ == "__main__":
    unittest.main()
