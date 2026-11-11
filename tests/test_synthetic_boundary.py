"""BayanGate Milestone BG-005 — Synthetic Accuracy & Boundary Test Suite.

Rigorously tests:
1. Complex multi-lingual synthetic documents (Arabic/English, contracts, KYC forms).
2. Eastern Arabic-Indic numerals (٠-٩) and Extended Persian/Urdu digits (۰-۹).
3. Tashkeel (Arabic diacritics) and Tatweel/Kashida (ـ) stress cases.
4. Clinging punctuation and enclosures (parentheses, brackets, quotes, Arabic commas/semicolons/question marks).
5. Boundary and negative inputs (empty strings, whitespace, single characters, non-PII numbers/dates/currencies).
6. Malformed and checksum-invalid candidate rejection (Saudi ID, Iqama, Emirates ID, Egyptian ID, GCC IBAN, Credit Card).
7. Large-scale document throughput, linearity, and zero coordinate drift.
8. Format preservation and RTL direction integrity under partial masking.
9. Deterministic HMAC pseudonym consistency and tamper-evident SHA-256 audit receipts.
"""

import time
import unittest
from typing import List

import bayan_gate
from bayan_gate.engine import RegionalPIIEngine
from bayan_gate.matchers import (
    validate_credit_card,
    validate_egyptian_national_id,
    validate_iban,
    validate_regional_phone,
    validate_saudi_national_id_or_iqama,
    validate_uae_emirates_id,
)
from bayan_gate.models import EntityType, MaskingPolicy, PIISpan, RedactionResult
from bayan_gate.normalizer import ArabicIndicNormalizer
from bayan_gate.redactor import PIIRedactor


class TestSyntheticMultiLingualDocuments(unittest.TestCase):
    """Exercises complex synthetic bilingual contracts and KYC agreements."""

    def setUp(self):
        self.engine = RegionalPIIEngine()
        self.redactor = PIIRedactor()

        # Complex synthetic bilingual KYC agreement containing 11 distinct PII types
        self.bilingual_kyc_doc = (
            "اتفاقية فتح حساب ومطابقة الهوية الوطنية والمصرفية (KYC Form)\n"
            "الطرف الأول: شركة البيان للحلول الرقمية، الرياض، المملكة العربية السعودية.\n"
            "الطرف الثاني: السيد أحمد بن خالد العتيبي، سعودي الجنسية.\n"
            "رقم الهوية الوطنية: 1082345678 (مسجل لدى مركز المعلومات الوطني).\n"
            "الممثل النظامي للمقيم: السيد سيرجي بتروف، رقم الإقامة: 2082345677.\n"
            "الفرع الإقليمي بدبي: رقم الهوية الإماراتية 784-1988-1234567-1.\n"
            "المستشار القانوني بالقاهرة: الرقم القومي المصري 29001011234567.\n"
            "بيانات الحسابات البنكية المعتمدة:\n"
            "1. الحساب السعودي: SA0380000000608010167519 (مصرف الراجحي)\n"
            "2. الحساب الإماراتي: AE070331234567890123456 (بنك الإمارات دبي الوطني)\n"
            "بطاقة الدفع المعتمدة للمصاريف: 4532 0150 1234 5671 (Visa Gold Corporate).\n"
            "أرقام الاتصال المباشرة:\n"
            "- جوال الرياض: +966 50 123 4567\n"
            "- جوال دبي: +971 50 123 4567\n"
            "- هاتف القاهرة: +20 10 1234 5678\n"
            "البريد الإلكتروني الرسمي: compliance-officer@bayangate.org\n"
            "عنوان خادم التدقيق: 192.168.1.100 ونطاق IPv6: 2001:0db8:85a3:0000:0000:8a2e:0370:7334\n"
            "تم التوقيع والمصادقة في تاريخ 2026-11-11."
        )

    def test_bilingual_kyc_document_all_entities_detected(self):
        """Verifies detection and exact grounding across all entities in complex bilingual doc."""
        spans = self.engine.detect(self.bilingual_kyc_doc)

        # Map detected spans by entity type
        by_type = {}
        for s in spans:
            by_type.setdefault(s.entity_type, []).append(s)
            # Verify exact unicode grounding
            self.assertTrue(s.verify_grounding(self.bilingual_kyc_doc))

        self.assertIn(EntityType.SAUDI_NATIONAL_ID, by_type)
        self.assertEqual(by_type[EntityType.SAUDI_NATIONAL_ID][0].raw_text, "1082345678")

        self.assertIn(EntityType.SAUDI_IQAMA, by_type)
        self.assertEqual(by_type[EntityType.SAUDI_IQAMA][0].raw_text, "2082345677")

        self.assertIn(EntityType.UAE_NATIONAL_ID, by_type)
        self.assertEqual(by_type[EntityType.UAE_NATIONAL_ID][0].raw_text, "784-1988-1234567-1")

        self.assertIn(EntityType.EGYPTIAN_NATIONAL_ID, by_type)
        self.assertEqual(by_type[EntityType.EGYPTIAN_NATIONAL_ID][0].raw_text, "29001011234567")

        self.assertIn(EntityType.GCC_IBAN, by_type)
        self.assertEqual(len(by_type[EntityType.GCC_IBAN]), 2)
        ibans = [s.raw_text for s in by_type[EntityType.GCC_IBAN]]
        self.assertIn("SA0380000000608010167519", ibans)
        self.assertIn("AE070331234567890123456", ibans)

        self.assertIn(EntityType.CREDIT_CARD, by_type)
        self.assertEqual(by_type[EntityType.CREDIT_CARD][0].raw_text, "4532 0150 1234 5671")

        self.assertIn(EntityType.PHONE_NUMBER, by_type)
        self.assertEqual(len(by_type[EntityType.PHONE_NUMBER]), 3)

        self.assertIn(EntityType.EMAIL_ADDRESS, by_type)
        self.assertEqual(by_type[EntityType.EMAIL_ADDRESS][0].raw_text, "compliance-officer@bayangate.org")

        self.assertIn(EntityType.IP_ADDRESS, by_type)
        ips = [s.raw_text for s in by_type[EntityType.IP_ADDRESS]]
        self.assertIn("192.168.1.100", ips)
        self.assertIn("2001:0db8:85a3:0000:0000:8a2e:0370:7334", ips)

    def test_bilingual_kyc_redaction_all_four_policies(self):
        """Verifies redaction transformation under all four policies without corrupting surrounding text."""
        # 1. REDACT_FULL
        res_full = self.redactor.redact(self.bilingual_kyc_doc, policy=MaskingPolicy.REDACT_FULL)
        self.assertNotIn("1082345678", res_full.redacted_text)
        self.assertNotIn("2082345677", res_full.redacted_text)
        self.assertNotIn("784-1988-1234567-1", res_full.redacted_text)
        self.assertNotIn("SA0380000000608010167519", res_full.redacted_text)
        self.assertIn("[REDACTED_SAUDI_NATIONAL_ID]", res_full.redacted_text)
        self.assertIn("[REDACTED_GCC_IBAN]", res_full.redacted_text)
        # Surrounding non-PII Arabic text remains intact
        self.assertIn("اتفاقية فتح حساب ومطابقة الهوية الوطنية", res_full.redacted_text)
        self.assertIn("السيد أحمد بن خالد العتيبي", res_full.redacted_text)

        # 2. MASK_PARTIAL
        res_partial = self.redactor.redact(self.bilingual_kyc_doc, policy=MaskingPolicy.MASK_PARTIAL)
        self.assertNotIn("1082345678", res_partial.redacted_text)
        self.assertIn("108****678", res_partial.redacted_text)
        self.assertIn("784-****-*******-1", res_partial.redacted_text)
        self.assertIn("SA03****************7519", res_partial.redacted_text)
        self.assertIn("4532 **** **** 5671", res_partial.redacted_text)

        # 3. PSEUDONYMIZE_HASH
        res_hash = self.redactor.redact(
            self.bilingual_kyc_doc,
            policy=MaskingPolicy.PSEUDONYMIZE_HASH,
            salt="enterprise-secret-salt-2026",
        )
        self.assertIn("[SA_ID_", res_hash.redacted_text)
        self.assertIn("[IBAN_", res_hash.redacted_text)
        self.assertIn("[TEL_", res_hash.redacted_text)
        self.assertIn("[CARD_", res_hash.redacted_text)

        # 4. REPLACE_SYNTHETIC
        res_synth = self.redactor.redact(self.bilingual_kyc_doc, policy=MaskingPolicy.REPLACE_SYNTHETIC)
        self.assertIn("1999999999", res_synth.redacted_text)
        self.assertIn("SA0000000000000000000000", res_synth.redacted_text)
        self.assertIn("4000000000000000", res_synth.redacted_text)


class TestEasternArabicIndicAndTashkeelStress(unittest.TestCase):
    """Exercises Eastern Arabic-Indic numerals, Persian/Urdu digits, Tashkeel, and Kashida."""

    def setUp(self):
        self.engine = RegionalPIIEngine()
        self.redactor = PIIRedactor()

    def test_eastern_arabic_indic_numeral_pii(self):
        """Verifies detection of IDs, IBANs, and Phones written in Eastern Arabic-Indic numerals (٠-٩)."""
        text = (
            "بيانات العميل:\n"
            "الهوية الوطنية: ١٠٨٢٣٤٥٦٧٨\n"
            "رقم الإقامة: ٢٠٨٢٣٤٥٦٧٧\n"
            "الهوية الإماراتية: ٧٨٤-١٩٨٨-١٢٣٤٥٦٧-١\n"
            "الرقم القومي المصري: ٢٩٠٠١٠١١٢٣٤٥٦٧\n"
            "رقم الجوال: ٠٥٠١٢٣٤٥٦٧\n"
            "البطاقة الائتمانية: ٤٥٣٢ ٠١٥٠ ١٢٣٤ ٥٦٧١"
        )
        spans = self.engine.detect(text)
        by_type = {s.entity_type: s for s in spans}

        self.assertIn(EntityType.SAUDI_NATIONAL_ID, by_type)
        self.assertEqual(by_type[EntityType.SAUDI_NATIONAL_ID].raw_text, "١٠٨٢٣٤٥٦٧٨")
        self.assertTrue(by_type[EntityType.SAUDI_NATIONAL_ID].verify_grounding(text))

        self.assertIn(EntityType.SAUDI_IQAMA, by_type)
        self.assertEqual(by_type[EntityType.SAUDI_IQAMA].raw_text, "٢٠٨٢٣٤٥٦٧٧")

        self.assertIn(EntityType.UAE_NATIONAL_ID, by_type)
        self.assertEqual(by_type[EntityType.UAE_NATIONAL_ID].raw_text, "٧٨٤-١٩٨٨-١٢٣٤٥٦٧-١")

        self.assertIn(EntityType.EGYPTIAN_NATIONAL_ID, by_type)
        self.assertEqual(by_type[EntityType.EGYPTIAN_NATIONAL_ID].raw_text, "٢٩٠٠١٠١١٢٣٤٥٦٧")

        self.assertIn(EntityType.PHONE_NUMBER, by_type)
        self.assertEqual(by_type[EntityType.PHONE_NUMBER].raw_text, "٠٥٠١٢٣٤٥٦٧")

        self.assertIn(EntityType.CREDIT_CARD, by_type)
        self.assertEqual(by_type[EntityType.CREDIT_CARD].raw_text, "٤٥٣٢ ٠١٥٠ ١٢٣٤ ٥٦٧١")

    def test_eastern_arabic_indic_numeral_redaction_preserves_script(self):
        """Verifies partial masking on Eastern numerals preserves Eastern numeral characters."""
        text = "الهوية: ١٠٨٢٣٤٥٦٧٨"
        res = self.redactor.redact(text, policy=MaskingPolicy.MASK_PARTIAL)
        self.assertEqual(res.redacted_text, "الهوية: ١٠٨****٦٧٨")

    def test_persian_urdu_extended_digits(self):
        """Verifies Persian/Urdu digits (۰۱۲۳۴۵۶۷۸۹) are normalized and detected."""
        text = "شماره ملی یا تلفن: ۰۵۰۱۲۳۴۵۶۷"
        spans = self.engine.detect(text)
        self.assertTrue(len(spans) >= 1)
        self.assertEqual(spans[0].entity_type, EntityType.PHONE_NUMBER)
        self.assertEqual(spans[0].raw_text, "۰۵۰۱۲۳۴۵۶۷")

    def test_tashkeel_vocalization_surrounding_pii(self):
        """Verifies zero-drift span grounding when text is heavily decorated with Tashkeel."""
        text = "تَحْقِيقُ الشَّخْصِيَّةِ: رَقْمُ الهُوِيَّةِ 1082345678 الصَّادِرَةُ مِنْ مَدِينَةِ الرِّيَاضِ."
        spans = self.engine.detect(text)
        self.assertEqual(len(spans), 1)
        span = spans[0]
        self.assertEqual(span.entity_type, EntityType.SAUDI_NATIONAL_ID)
        self.assertEqual(span.raw_text, "1082345678")
        self.assertTrue(span.verify_grounding(text))

        # Redact and verify vocalized text is preserved
        res = self.redactor.redact(text, policy=MaskingPolicy.REDACT_FULL)
        self.assertIn("تَحْقِيقُ الشَّخْصِيَّةِ: رَقْمُ الهُوِيَّةِ [REDACTED_SAUDI_NATIONAL_ID] الصَّادِرَةُ مِنْ مَدِينَةِ الرِّيَاضِ.", res.redacted_text)

    def test_tatweel_kashida_elongation_surrounding_pii(self):
        """Verifies zero-drift span grounding with typographical Tatweel elongation."""
        text = "رقـــــمـ الهــــويـة: 1082345678 و الجــــوال: 0501234567"
        spans = self.engine.detect(text)
        self.assertEqual(len(spans), 2)
        for s in spans:
            self.assertTrue(s.verify_grounding(text))

        res = self.redactor.redact(text, policy=MaskingPolicy.REPLACE_SYNTHETIC)
        self.assertIn("رقـــــمـ الهــــويـة: 1999999999", res.redacted_text)
        self.assertIn("الجــــوال: 0500000000", res.redacted_text)


class TestClingingPunctuationAndEnclosures(unittest.TestCase):
    """Exercises punctuation immediately adjacent to, wrapping, or clinging to PII."""

    def setUp(self):
        self.engine = RegionalPIIEngine()
        self.redactor = PIIRedactor()

    def test_parentheses_and_brackets_enclosing_pii(self):
        """Verifies identifiers wrapped in parentheses, brackets, and braces are accurately isolated."""
        samples = [
            ("رقم الهوية: (1082345678)", "1082345678", EntityType.SAUDI_NATIONAL_ID),
            ("رقم الإقامة: [2082345677]", "2082345677", EntityType.SAUDI_IQAMA),
            ("حساب الآيبان: {SA0380000000608010167519}", "SA0380000000608010167519", EntityType.GCC_IBAN),
            ("الهاتف: (0501234567)", "0501234567", EntityType.PHONE_NUMBER),
            ("الهاتف الدولي: (+966 50 123 4567)", "+966 50 123 4567", EntityType.PHONE_NUMBER),
        ]
        for text, expected_raw, expected_type in samples:
            spans = self.engine.detect(text)
            self.assertEqual(len(spans), 1, f"Failed detection on: {text}")
            self.assertEqual(spans[0].entity_type, expected_type)
            self.assertEqual(spans[0].raw_text, expected_raw)
            self.assertTrue(spans[0].verify_grounding(text))

    def test_quotation_marks_and_guillemets(self):
        """Verifies PII enclosed in English and Arabic quotation marks."""
        text = 'وثائق: "1082345678" و \'2082345677\' و «784-1988-1234567-1» و “4532 0150 1234 5671”'
        spans = self.engine.detect(text)
        self.assertEqual(len(spans), 4)
        for s in spans:
            self.assertTrue(s.verify_grounding(text))
            self.assertFalse(s.raw_text.startswith(('"', "'", "«", "“")))
            self.assertFalse(s.raw_text.endswith(('"', "'", "»", "”")))

    def test_adjacent_arabic_and_latin_punctuation(self):
        """Verifies trailing periods, commas, Arabic commas، question marks؟, semicolons؛."""
        text = "هل الهوية 1082345678؟ نعم، والآيبان SA0380000000608010167519؛ للتأكيد: 0501234567."
        spans = self.engine.detect(text)
        self.assertEqual(len(spans), 3)

        raw_values = [s.raw_text for s in spans]
        self.assertEqual(raw_values[0], "1082345678")
        self.assertEqual(raw_values[1], "SA0380000000608010167519")
        self.assertEqual(raw_values[2], "0501234567")

        res = self.redactor.redact(text, policy=MaskingPolicy.REDACT_FULL)
        self.assertIn("هل الهوية [REDACTED_SAUDI_NATIONAL_ID]؟", res.redacted_text)
        self.assertIn("نعم، والآيبان [REDACTED_GCC_IBAN]؛", res.redacted_text)
        self.assertIn("للتأكيد: [REDACTED_PHONE_NUMBER].", res.redacted_text)

    def test_currency_and_measurement_distinction(self):
        """Verifies currency amounts (SAR 15,000, 500 AED) are not misclassified as PII."""
        text = "المبلغ الإجمالي هو 15000 SAR أو 50,000 ر.س مع خصم 15% على 200 قطعة."
        spans = self.engine.detect(text)
        self.assertEqual(len(spans), 0)


class TestEdgeAndBoundaryInputs(unittest.TestCase):
    """Exercises extreme edge cases, empty values, single characters, and non-PII text."""

    def setUp(self):
        self.engine = RegionalPIIEngine()
        self.redactor = PIIRedactor()

    def test_empty_string_and_whitespace(self):
        """Verifies empty and whitespace strings return safely without exceptions."""
        self.assertEqual(self.engine.detect(""), [])
        self.assertEqual(self.engine.detect("   "), [])
        self.assertEqual(self.engine.detect("\t\n\r\n"), [])

        res_empty = self.redactor.redact("", policy=MaskingPolicy.REDACT_FULL)
        self.assertEqual(res_empty.redacted_text, "")
        self.assertEqual(res_empty.redaction_count, 0)

        res_ws = self.redactor.redact("  \n\t  ", policy=MaskingPolicy.REDACT_FULL)
        self.assertEqual(res_ws.redacted_text, "  \n\t  ")

    def test_single_characters_and_tiny_strings(self):
        """Verifies single characters do not trigger regex errors or false positives."""
        for char in ["a", "1", "١", "ـ", "@", "+", "-", ".", " ", "\n"]:
            self.assertEqual(self.engine.detect(char), [])
            res = self.redactor.redact(char)
            self.assertEqual(res.redacted_text, char)

    def test_common_non_pii_numbers_and_dates(self):
        """Verifies standard numbers, years, dates, and order codes are not flagged."""
        non_pii = (
            "سنة التأسيس: 1999 أو 2024\n"
            "تاريخ الاجتماع: 2026-11-11 أو 15/05/2025\n"
            "رقم الطلب: ORD-998877 أو INV-123456\n"
            "الوزن: 450 كجم، السرعة: 120 كم/ساعة\n"
            "درجة الحرارة: 37.5 مئوية"
        )
        spans = self.engine.detect(non_pii)
        self.assertEqual(len(spans), 0)

    def test_non_pii_literary_arabic_text(self):
        """Verifies classical Arabic literary prose has zero false positive detections."""
        prose = (
            "وإذا سألت عن البيان وفضله، فاعلم أنه مرآة الفكر وسبيل البلاغة، "
            "وقد سار في الآفاق حديثه، وازدهرت به معارف الأجداد عبر القرون المتطاولة."
        )
        spans = self.engine.detect(prose)
        self.assertEqual(len(spans), 0)


class TestNegativeMalformedChecksumCandidates(unittest.TestCase):
    """Exercises malformed identifiers that should fail checksum or structural rules."""

    def setUp(self):
        self.engine = RegionalPIIEngine()

    def test_malformed_saudi_ids(self):
        """Verifies rejection of invalid length, non-conforming digits, and invalid Luhn check."""
        # Too short (9 digits)
        self.assertFalse(validate_saudi_national_id_or_iqama("108234567")[0])
        # Too long (11 digits)
        self.assertFalse(validate_saudi_national_id_or_iqama("10823456789")[0])
        # Starts with 3 (invalid category)
        self.assertFalse(validate_saudi_national_id_or_iqama("3082345678")[0])
        # Invalid Luhn checksum (last digit flipped from 8 to 9)
        is_valid, _, meta = validate_saudi_national_id_or_iqama("1082345679")
        self.assertFalse(meta.get("is_valid_checksum", False))

    def test_malformed_egyptian_national_ids(self):
        """Verifies rejection of invalid century, invalid month, invalid day, and invalid gov."""
        # Invalid century (starts with 1)
        self.assertFalse(validate_egyptian_national_id("19001011234567")[0])
        # Invalid month (month 13)
        self.assertFalse(validate_egyptian_national_id("29013011234567")[0])
        # Invalid day (day 32)
        self.assertFalse(validate_egyptian_national_id("29001321234567")[0])
        # Invalid governorate code 99 (Egypt codes are 01-35, 88)
        self.assertFalse(validate_egyptian_national_id("29001019934567")[0])
        # Too short (13 digits)
        self.assertFalse(validate_egyptian_national_id("2900101123456")[0])

    def test_malformed_uae_emirates_ids(self):
        """Verifies rejection of non-784 prefix and out-of-range birth year."""
        # Wrong country prefix (785 instead of 784)
        self.assertFalse(validate_uae_emirates_id("785-1988-1234567-1")[0])
        # Out-of-bounds birth year (1890)
        self.assertFalse(validate_uae_emirates_id("784-1890-1234567-1")[0])
        # Wrong length (14 digits)
        self.assertFalse(validate_uae_emirates_id("784-1988-123456-1")[0])

    def test_malformed_gcc_ibans(self):
        """Verifies rejection of invalid MOD 97-10 checksums."""
        # Valid Saudi IBAN is SA0380000000608010167519; corrupt last digit to 8
        is_valid, _, _ = validate_iban("SA0380000000608010167518")
        self.assertFalse(is_valid)
        # Corrupted country code
        is_valid, _, _ = validate_iban("XX0380000000608010167519")
        self.assertFalse(is_valid)

    def test_malformed_credit_cards(self):
        """Verifies rejection of invalid Luhn payment cards."""
        # Valid Visa 4532 0150 1234 5671; corrupt last digit to 2
        is_valid, _ = validate_credit_card("4532 0150 1234 5672")
        self.assertFalse(is_valid)
        # Too short (12 digits)
        is_valid, _ = validate_credit_card("4532 0150 1234")
        self.assertFalse(is_valid)

    def test_malformed_phone_numbers(self):
        """Verifies rejection of truncated or invalid phone prefixes."""
        # Truncated dial code
        self.assertFalse(validate_regional_phone("+9665")[0])
        # Invalid mobile prefix in Saudi Arabia (04 is landline, not 10-digit mobile)
        self.assertFalse(validate_regional_phone("0401234567")[0])


class TestLargeDocumentThroughputAndLinearity(unittest.TestCase):
    """Verifies throughput, linear scalability, and zero offset drift on large documents."""

    def setUp(self):
        self.engine = RegionalPIIEngine()
        self.redactor = PIIRedactor()

    def test_large_corpus_throughput_and_drift_verification(self):
        """Generates a 50+ KB synthetic document with hundreds of PII items and verifies performance."""
        paragraphs = []
        for i in range(100):
            p = (
                f"الفقرة رقم {i}: قام العميل ذو الهوية الوطنية 1082345678 بالاتصال "
                f"من رقم هاتفه 0501234567 لتأكيد تحويل مصرفي إلى الآيبان SA0380000000608010167519. "
                f"تمت العملية بواسطة البطاقة 4532 0150 1234 5671 والمستشار 29001011234567.\n"
            )
            paragraphs.append(p)

        large_doc = "".join(paragraphs)
        self.assertGreater(len(large_doc), 20000)

        # Measure detection execution time
        t0 = time.perf_counter()
        spans = self.engine.detect(large_doc)
        t_detect = time.perf_counter() - t0

        # Must detect exactly 5 entities per paragraph (500 total)
        self.assertEqual(len(spans), 500)
        # Linear performance: detection on 500 entities must complete quickly
        self.assertLess(t_detect, 2.0, f"Detection was too slow: {t_detect:.2f}s")

        # Verify zero drift on every detected span across the 25,000+ char document
        for s in spans:
            self.assertTrue(s.verify_grounding(large_doc))

        # Measure redaction execution time
        t1 = time.perf_counter()
        res = self.redactor.redact(large_doc, policy=MaskingPolicy.MASK_PARTIAL)
        t_redact = time.perf_counter() - t1

        self.assertLess(t_redact, 1.0, f"Redaction was too slow: {t_redact:.2f}s")
        self.assertEqual(res.redaction_count, 500)
        self.assertNotIn("1082345678", res.redacted_text)
        self.assertIn("108****678", res.redacted_text)


class TestPseudonymConsistencyAndAuditReceipts(unittest.TestCase):
    """Verifies deterministic pseudonym tokens and cryptographic SHA-256 audit integrity."""

    def setUp(self):
        self.redactor = PIIRedactor()

    def test_pseudonym_consistency_across_calls_with_same_salt(self):
        """Verifies identical inputs produce identical HMAC pseudonyms given the same salt."""
        text1 = "العميل الأول هويته 1082345678 وهاتفه 0501234567"
        text2 = "العميل الثاني يشارك الهوية 1082345678 وهاتفه 0501234567"

        salt = "salt-consistency-test-key-2026"
        res1 = self.redactor.redact(text1, policy=MaskingPolicy.PSEUDONYMIZE_HASH, salt=salt)
        res2 = self.redactor.redact(text2, policy=MaskingPolicy.PSEUDONYMIZE_HASH, salt=salt)

        # Extract tokens for 1082345678
        token_id_1 = [w for w in res1.redacted_text.split() if w.startswith("[SA_ID_")][0]
        token_id_2 = [w for w in res2.redacted_text.split() if w.startswith("[SA_ID_")][0]
        self.assertEqual(token_id_1, token_id_2)

        # Extract tokens for 0501234567
        token_phone_1 = [w for w in res1.redacted_text.split() if w.startswith("[TEL_")][0]
        token_phone_2 = [w for w in res2.redacted_text.split() if w.startswith("[TEL_")][0]
        self.assertEqual(token_phone_1, token_phone_2)

    def test_pseudonym_divergence_with_different_salts(self):
        """Verifies different salts yield completely different pseudonym tokens."""
        text = "الهوية 1082345678"
        res_salt_a = self.redactor.redact(text, policy=MaskingPolicy.PSEUDONYMIZE_HASH, salt="salt-alpha")
        res_salt_b = self.redactor.redact(text, policy=MaskingPolicy.PSEUDONYMIZE_HASH, salt="salt-beta")

        self.assertNotEqual(res_salt_a.redacted_text, res_salt_b.redacted_text)

    def test_tamper_evident_sha256_audit_hash(self):
        """Verifies SHA-256 audit hash changes if any input or transformation changes."""
        text_a = "الهوية 1082345678"
        text_b = "الهوية 1082345677"  # Different number

        res_a1 = self.redactor.redact(text_a, policy=MaskingPolicy.REDACT_FULL)
        res_a2 = self.redactor.redact(text_a, policy=MaskingPolicy.REDACT_FULL)
        res_b = self.redactor.redact(text_b, policy=MaskingPolicy.REDACT_FULL)

        # Repeatable hashing
        self.assertEqual(res_a1.audit_hash, res_a2.audit_hash)
        self.assertEqual(len(res_a1.audit_hash), 64)
        # Divergent hashing for different content
        self.assertNotEqual(res_a1.audit_hash, res_b.audit_hash)

    def test_zero_sensitive_logging_in_audit_export(self):
        """Verifies default dictionary serialization masks raw entity strings to prevent leakage."""
        text = "الهوية 1082345678 والهاتف 0501234567"
        res = self.redactor.redact(text, policy=MaskingPolicy.REDACT_FULL)

        safe_dict = res.to_dict(include_raw_spans=False)
        self.assertEqual(safe_dict["entities"][0]["raw_text"], "[LENGTH_10]")
        self.assertEqual(safe_dict["entities"][1]["raw_text"], "[LENGTH_10]")

        # Only when explicitly requested are raw spans exported
        unsafe_dict = res.to_dict(include_raw_spans=True)
        self.assertEqual(unsafe_dict["entities"][0]["raw_text"], "1082345678")
        self.assertEqual(unsafe_dict["entities"][1]["raw_text"], "0501234567")


if __name__ == "__main__":
    unittest.main()
