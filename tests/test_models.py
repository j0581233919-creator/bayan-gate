"""Unit tests for BayanGate data models (BG-001)."""

import unittest
from bayan_gate.models import (
    EntityType,
    MaskingPolicy,
    PIISpan,
    RedactionResult,
)


class TestBayanGateModels(unittest.TestCase):
    def test_entity_type_enum(self):
        self.assertEqual(EntityType.SAUDI_NATIONAL_ID.value, "SAUDI_NATIONAL_ID")
        self.assertEqual(EntityType.SAUDI_IQAMA.value, "SAUDI_IQAMA")
        self.assertEqual(EntityType.UAE_NATIONAL_ID.value, "UAE_NATIONAL_ID")
        self.assertEqual(EntityType.EGYPTIAN_NATIONAL_ID.value, "EGYPTIAN_NATIONAL_ID")
        self.assertEqual(EntityType.GCC_IBAN.value, "GCC_IBAN")
        self.assertEqual(EntityType.PHONE_NUMBER.value, "PHONE_NUMBER")
        self.assertEqual(EntityType.CREDIT_CARD.value, "CREDIT_CARD")
        self.assertEqual(EntityType.EMAIL_ADDRESS.value, "EMAIL_ADDRESS")

    def test_masking_policy_enum(self):
        self.assertEqual(MaskingPolicy.REDACT_FULL.value, "REDACT_FULL")
        self.assertEqual(MaskingPolicy.MASK_PARTIAL.value, "MASK_PARTIAL")
        self.assertEqual(MaskingPolicy.PSEUDONYMIZE_HASH.value, "PSEUDONYMIZE_HASH")
        self.assertEqual(MaskingPolicy.REPLACE_SYNTHETIC.value, "REPLACE_SYNTHETIC")

    def test_pii_span_creation_and_properties(self):
        span = PIISpan(
            entity_type=EntityType.SAUDI_NATIONAL_ID,
            raw_text="١٠٨٢٣٤٥٦٧٨",
            normalized_text="1082345678",
            start_char=10,
            end_char=20,
            confidence=0.98,
            metadata={"country": "SA", "id_type": "citizen"},
            is_valid_checksum=True,
        )
        self.assertEqual(span.span_length, 10)
        self.assertEqual(span.entity_type, EntityType.SAUDI_NATIONAL_ID)
        self.assertEqual(span.raw_text, "١٠٨٢٣٤٥٦٧٨")
        self.assertEqual(span.normalized_text, "1082345678")
        self.assertEqual(span.confidence, 0.98)
        self.assertTrue(span.is_valid_checksum)

    def test_pii_span_validation_guards(self):
        # Negative start_char
        with self.assertRaises(ValueError):
            PIISpan(
                entity_type=EntityType.PHONE_NUMBER,
                raw_text="0501234567",
                normalized_text="0501234567",
                start_char=-1,
                end_char=10,
            )

        # end_char <= start_char
        with self.assertRaises(ValueError):
            PIISpan(
                entity_type=EntityType.PHONE_NUMBER,
                raw_text="0501234567",
                normalized_text="0501234567",
                start_char=10,
                end_char=10,
            )

        with self.assertRaises(ValueError):
            PIISpan(
                entity_type=EntityType.PHONE_NUMBER,
                raw_text="0501234567",
                normalized_text="0501234567",
                start_char=15,
                end_char=10,
            )

        # Invalid confidence
        with self.assertRaises(ValueError):
            PIISpan(
                entity_type=EntityType.PHONE_NUMBER,
                raw_text="0501234567",
                normalized_text="0501234567",
                start_char=0,
                end_char=10,
                confidence=1.5,
            )

        with self.assertRaises(ValueError):
            PIISpan(
                entity_type=EntityType.PHONE_NUMBER,
                raw_text="0501234567",
                normalized_text="0501234567",
                start_char=0,
                end_char=10,
                confidence=-0.1,
            )

    def test_pii_span_verify_grounding(self):
        doc = "الهوية: ١٠٨٢٣٤٥٦٧٨ المسجلة."
        # Substring "١٠٨٢٣٤٥٦٧٨" is at index 8..18
        span = PIISpan(
            entity_type=EntityType.SAUDI_NATIONAL_ID,
            raw_text="١٠٨٢٣٤٥٦٧٨",
            normalized_text="1082345678",
            start_char=8,
            end_char=18,
        )
        self.assertTrue(span.verify_grounding(doc))

        # Off-by-one span
        bad_span = PIISpan(
            entity_type=EntityType.SAUDI_NATIONAL_ID,
            raw_text="١٠٨٢٣٤٥٦٧٨",
            normalized_text="1082345678",
            start_char=7,
            end_char=17,
        )
        self.assertFalse(bad_span.verify_grounding(doc))

        # Out-of-bounds span
        oob_span = PIISpan(
            entity_type=EntityType.SAUDI_NATIONAL_ID,
            raw_text="١٠٨٢٣٤٥٦٧٨",
            normalized_text="1082345678",
            start_char=50,
            end_char=60,
        )
        self.assertFalse(oob_span.verify_grounding(doc))

    def test_pii_span_serialization_roundtrip(self):
        span = PIISpan(
            entity_type=EntityType.GCC_IBAN,
            raw_text="SA0380000000608010167519",
            normalized_text="SA0380000000608010167519",
            start_char=5,
            end_char=29,
            confidence=1.0,
            metadata={"bank": "Al Rajhi Bank", "country": "SA"},
            is_valid_checksum=True,
        )
        d = span.to_dict()
        reconstructed = PIISpan.from_dict(d)
        self.assertEqual(span, reconstructed)

    def test_redaction_result_properties_and_safe_serialization(self):
        span1 = PIISpan(
            entity_type=EntityType.SAUDI_NATIONAL_ID,
            raw_text="1082345678",
            normalized_text="1082345678",
            start_char=0,
            end_char=10,
        )
        span2 = PIISpan(
            entity_type=EntityType.PHONE_NUMBER,
            raw_text="+966501234567",
            normalized_text="+966501234567",
            start_char=15,
            end_char=28,
        )

        res = RedactionResult(
            original_length=50,
            redacted_text="[REDACTED_SAUDI_NATIONAL_ID] - [REDACTED_PHONE_NUMBER]",
            entities_detected=[span1, span2],
            policy_applied=MaskingPolicy.REDACT_FULL,
            audit_hash="sha256_mock_hash",
        )

        self.assertEqual(res.redaction_count, 2)
        self.assertEqual(res.entity_type_counts, {
            "SAUDI_NATIONAL_ID": 1,
            "PHONE_NUMBER": 1,
        })

        # Test Zero-Sensitive Logging (include_raw_spans=False by default)
        safe_dict = res.to_dict(include_raw_spans=False)
        self.assertEqual(safe_dict["entities"][0]["raw_text"], "[LENGTH_10]")
        self.assertEqual(safe_dict["entities"][1]["raw_text"], "[LENGTH_13]")
        self.assertNotIn("1082345678", str(safe_dict))
        self.assertNotIn("+966501234567", str(safe_dict))

        # Explicit raw inclusion (when caller specifically requests it for local memory processing)
        raw_dict = res.to_dict(include_raw_spans=True)
        self.assertEqual(raw_dict["entities"][0]["raw_text"], "1082345678")


if __name__ == "__main__":
    unittest.main()
