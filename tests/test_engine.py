"""Integration and behavioral tests for RegionalPIIEngine (BG-002)."""

import unittest
from bayan_gate.engine import RegionalPIIEngine
from bayan_gate.models import EntityType


class TestRegionalPIIEngine(unittest.TestCase):
    def setUp(self):
        self.engine = RegionalPIIEngine()

    def test_detect_empty_or_whitespace(self):
        self.assertEqual(self.engine.detect(""), [])
        self.assertEqual(self.engine.detect("   \n\t  "), [])

    def test_detect_saudi_national_id_eastern_numerals(self):
        # Text with diacritics and Eastern Arabic-Indic numerals
        text = "رَقْمُ الهُوِيَّةِ الوَطَنِيَّةِ: ١٠٨٢٣٤٥٦٧٨ في النظام"
        spans = self.engine.detect(text)

        self.assertEqual(len(spans), 1)
        span = spans[0]
        self.assertEqual(span.entity_type, EntityType.SAUDI_NATIONAL_ID)
        self.assertEqual(span.raw_text, "١٠٨٢٣٤٥٦٧٨")
        self.assertEqual(span.normalized_text, "1082345678")
        self.assertTrue(span.verify_grounding(text))

        # Check coordinates in original string
        self.assertEqual(text[span.start_char:span.end_char], "١٠٨٢٣٤٥٦٧٨")

    def test_detect_saudi_iqama_western_numerals(self):
        text = "رقم الإقامة للمقيم: 2082345678 في الرياض"
        spans = self.engine.detect(text)

        self.assertEqual(len(spans), 1)
        span = spans[0]
        self.assertEqual(span.entity_type, EntityType.SAUDI_IQAMA)
        self.assertEqual(span.raw_text, "2082345678")
        self.assertTrue(span.verify_grounding(text))

    def test_detect_uae_emirates_id_with_dashes_and_eastern(self):
        text = "بطاقة الهوية الإماراتية: ٧٨٤-١٩٩٠-١٢٣٤٥٦٧-١"
        spans = self.engine.detect(text)

        self.assertEqual(len(spans), 1)
        span = spans[0]
        self.assertEqual(span.entity_type, EntityType.UAE_NATIONAL_ID)
        self.assertEqual(span.raw_text, "٧٨٤-١٩٩٠-١٢٣٤٥٦٧-١")
        self.assertEqual(span.normalized_text, "784-1990-1234567-1")
        self.assertEqual(span.metadata["birth_year"], 1990)
        self.assertTrue(span.verify_grounding(text))

    def test_detect_egyptian_national_id(self):
        # Born 1990-05-15, Cairo (01), Male
        text = "الرقم القومي المصري: 29005150112314 الصادر من القاهرة"
        spans = self.engine.detect(text)

        self.assertEqual(len(spans), 1)
        span = spans[0]
        self.assertEqual(span.entity_type, EntityType.EGYPTIAN_NATIONAL_ID)
        self.assertEqual(span.raw_text, "29005150112314")
        self.assertEqual(span.metadata["birth_date"], "1990-05-15")
        self.assertEqual(span.metadata["governorate_name"], "Cairo")
        self.assertTrue(span.verify_grounding(text))

    def test_detect_gcc_iban_in_arabic_context(self):
        text = "يرجى تحويل الرسوم إلى الآيبان: SA03 8000 0000 6080 1016 7519 مصرف الراجحي"
        spans = self.engine.detect(text)

        self.assertEqual(len(spans), 1)
        span = spans[0]
        self.assertEqual(span.entity_type, EntityType.GCC_IBAN)
        self.assertEqual(span.metadata["country_code"], "SA")
        self.assertTrue(span.is_valid_checksum)
        self.assertTrue(span.verify_grounding(text))

    def test_detect_credit_card_and_phone(self):
        text = "Card: 4532 0150 1234 5671, Contact: +966501234567"
        spans = self.engine.detect(text)

        self.assertEqual(len(spans), 2)
        types = [s.entity_type for s in spans]
        self.assertIn(EntityType.CREDIT_CARD, types)
        self.assertIn(EntityType.PHONE_NUMBER, types)

        for s in spans:
            self.assertTrue(s.verify_grounding(text))

    def test_detect_email_and_ip(self):
        text = "Send reports to support@example.sa or connect via 192.168.1.100"
        spans = self.engine.detect(text)

        self.assertEqual(len(spans), 2)
        self.assertEqual(spans[0].entity_type, EntityType.EMAIL_ADDRESS)
        self.assertEqual(spans[0].raw_text, "support@example.sa")
        self.assertEqual(spans[1].entity_type, EntityType.IP_ADDRESS)
        self.assertEqual(spans[1].raw_text, "192.168.1.100")

    def test_overlap_resolution_iban_vs_phone(self):
        # An IBAN like SA0380000000608010167519 contains substrings of digits that could resemble a phone
        text = "IBAN: SA0380000000608010167519"
        spans = self.engine.detect(text)

        # Should only detect the GCC_IBAN, not a spurious phone number sub-slice
        self.assertEqual(len(spans), 1)
        self.assertEqual(spans[0].entity_type, EntityType.GCC_IBAN)

    def test_enabled_types_filter(self):
        text = "Citizen ID: 1082345678, Phone: 0501234567"
        # Only detect SAUDI_NATIONAL_ID
        spans = self.engine.detect(text, enabled_types={EntityType.SAUDI_NATIONAL_ID})
        self.assertEqual(len(spans), 1)
        self.assertEqual(spans[0].entity_type, EntityType.SAUDI_NATIONAL_ID)

    def test_mixed_arabic_document_multi_entity(self):
        # Comprehensive realistic MENA document
        doc = (
            "عقد توريد وخدمات:\n"
            "الطرف الأول: شركة الأفق (سجل: 1010123456)\n"
            "الممثل: محمد، هوية وطنية: ١٠٨٢٣٤٥٦٧٨\n"
            "هاتف: ٠٥٠١٢٣٤٥٦٧، بريد: info@al-ofooq.sa\n"
            "الحساب البنكي: SA03 8000 0000 6080 1016 7519\n"
        )
        spans = self.engine.detect(doc)

        self.assertTrue(len(spans) >= 4)
        found_types = {s.entity_type for s in spans}
        self.assertIn(EntityType.SAUDI_NATIONAL_ID, found_types)
        self.assertIn(EntityType.PHONE_NUMBER, found_types)
        self.assertIn(EntityType.EMAIL_ADDRESS, found_types)
        self.assertIn(EntityType.GCC_IBAN, found_types)

        # Every single span must be 100% verifiable in the raw document
        for s in spans:
            self.assertTrue(s.verify_grounding(doc), f"Failed grounding for {s}")

    def test_detect_gcc_iban_with_eastern_arabic_numerals(self):
        text = "الحساب البنكي: SA٠٣ ٨٠٠٠ ٠٠٠٠ ٦٠٨٠ ١٠١٦ ٧٥١٩ للتحويل"
        spans = self.engine.detect(text)

        self.assertEqual(len(spans), 1)
        span = spans[0]
        self.assertEqual(span.entity_type, EntityType.GCC_IBAN)
        self.assertEqual(span.raw_text, "SA٠٣ ٨٠٠٠ ٠٠٠٠ ٦٠٨٠ ١٠١٦ ٧٥١٩")
        self.assertEqual(span.normalized_text, "SA0380000000608010167519")
        self.assertTrue(span.is_valid_checksum)
        self.assertTrue(span.verify_grounding(text))

    def test_detect_kuwait_and_qatar_phones(self):
        text = "Kuwait: +96598765432, Qatar: +97433123456"
        spans = self.engine.detect(text)

        self.assertEqual(len(spans), 2)
        self.assertEqual(spans[0].metadata["country_code"], "KW")
        self.assertEqual(spans[1].metadata["country_code"], "QA")
        for s in spans:
            self.assertTrue(s.verify_grounding(text))

    def test_min_confidence_filter(self):
        text = "Citizen ID: 1082345678"
        # High confidence filter
        spans_high = self.engine.detect(text, min_confidence=0.999)
        self.assertEqual(len(spans_high), 0)

        # Standard confidence filter
        spans_std = self.engine.detect(text, min_confidence=0.5)
        self.assertEqual(len(spans_std), 1)


if __name__ == "__main__":
    unittest.main()
