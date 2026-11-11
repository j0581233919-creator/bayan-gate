"""Unit tests for ArabicIndicNormalizer and SpanMapper (BG-001)."""

import unittest
from bayan_gate.normalizer import (
    ArabicIndicNormalizer,
    EASTERN_ARABIC_INDIC_DIGITS,
    EXTENDED_ARABIC_INDIC_DIGITS,
    WESTERN_ARABIC_DIGITS,
)


class TestArabicIndicNormalizer(unittest.TestCase):
    # -------------------------------------------------------------
    # 1. Numeral Translation Tests
    # -------------------------------------------------------------
    def test_to_western_digits_eastern(self):
        eastern = "٠١٢٣٤٥٦٧٨٩"
        expected = "0123456789"
        self.assertEqual(ArabicIndicNormalizer.to_western_digits(eastern), expected)

    def test_to_western_digits_extended_persian(self):
        persian = "۰۱۲۳۴۵۶۷۸۹"
        expected = "0123456789"
        self.assertEqual(ArabicIndicNormalizer.to_western_digits(persian), expected)

    def test_to_arabic_indic_digits(self):
        western = "0123456789"
        expected = "٠١٢٣٤٥٦٧٨٩"
        self.assertEqual(ArabicIndicNormalizer.to_arabic_indic_digits(western), expected)

    def test_numeral_roundtrip(self):
        orig = "0123456789"
        eastern = ArabicIndicNormalizer.to_arabic_indic_digits(orig)
        back = ArabicIndicNormalizer.to_western_digits(eastern)
        self.assertEqual(back, orig)

    def test_mixed_digits_in_text(self):
        mixed = "الهاتف: ٠٥٠-123-٤٥٦٧ والرقم: ٩٩١"
        expected = "الهاتف: 050-123-4567 والرقم: 991"
        self.assertEqual(ArabicIndicNormalizer.to_western_digits(mixed), expected)

    def test_has_arabic_indic_digits(self):
        self.assertTrue(ArabicIndicNormalizer.has_arabic_indic_digits("رقم: ٤٥"))
        self.assertTrue(ArabicIndicNormalizer.has_arabic_indic_digits("کد: ۵۶"))
        self.assertFalse(ArabicIndicNormalizer.has_arabic_indic_digits("رقم: 45"))
        self.assertFalse(ArabicIndicNormalizer.has_arabic_indic_digits("نص بدون أرقام"))
        self.assertFalse(ArabicIndicNormalizer.has_arabic_indic_digits(""))

    def test_has_arabic_text(self):
        self.assertTrue(ArabicIndicNormalizer.has_arabic_text("مرحبا"))
        self.assertTrue(ArabicIndicNormalizer.has_arabic_text("Hello بالعالم"))
        self.assertFalse(ArabicIndicNormalizer.has_arabic_text("Hello World 123"))
        self.assertFalse(ArabicIndicNormalizer.has_arabic_text(""))

    # -------------------------------------------------------------
    # 2. Tashkeel / Harakat Normalization & Span Mapping
    # -------------------------------------------------------------
    def test_normalize_text_tashkeel_removal(self):
        # "رَقْمُ" has diacritics: Fatha on Raa, Sukun on Qaf, Damma on Meem
        text = "رَقْمُ الهُوِيَّةِ"
        res = ArabicIndicNormalizer.normalize_text(text, strip_tashkeel=True)
        self.assertEqual(res.normalized_text, "رقم الهوية")
        self.assertEqual(len(res.normalized_text), len(res.index_map))

    def test_normalize_text_span_mapping_precision(self):
        # Input with diacritics and eastern digits:
        # "رَقْمُ: ١٠٨٢٣٤٥٦٧٨"
        # Let's inspect character-by-character mapping
        text = "رَقْمُ: ١٠٨٢٣٤٥٦٧٨"
        res = ArabicIndicNormalizer.normalize_text(
            text,
            strip_tashkeel=True,
            convert_digits=True,
        )
        self.assertEqual(res.normalized_text, "رقم: 1082345678")

        # Find "1082345678" in normalized text
        norm_start = res.normalized_text.index("1082345678")
        norm_end = norm_start + len("1082345678")

        # Map back to original
        orig_start, orig_end = res.map_span_to_original(norm_start, norm_end)
        extracted = text[orig_start:orig_end]

        # The extracted original substring must match the Eastern digits
        self.assertEqual(extracted, "١٠٨٢٣٤٥٦٧٨")

    def test_normalize_text_tatweel_kashida(self):
        # Tatweel elongation: "ســــلام"
        text = "ســــلام"
        res = ArabicIndicNormalizer.normalize_text(text, strip_tatweel=True)
        self.assertEqual(res.normalized_text, "سلام")

        # "س" in normalized text is at [0:1]; its original span includes attached tatweels [0:5]
        orig_start, orig_end = res.map_span_to_original(0, 1)
        self.assertEqual(text[orig_start:orig_end], "ســــ")

        # "لام" in normalized text is at [1:4]; its original span is [5:8] ("لام")
        orig_start, orig_end = res.map_span_to_original(1, 4)
        self.assertEqual(text[orig_start:orig_end], "لام")

    def test_normalize_text_alef_and_teh_marbuta(self):
        text = "إدارة الأجهزة"
        res = ArabicIndicNormalizer.normalize_text(
            text,
            normalize_alef=True,
            normalize_teh_marbuta=True,
        )
        self.assertEqual(res.normalized_text, "اداره الاجهزه")
        self.assertEqual(len(res.normalized_text), len(text))
        self.assertEqual(res.index_map, list(range(len(text))))

    def test_span_mapping_boundary_cases(self):
        text = "أهْلاً"
        res = ArabicIndicNormalizer.normalize_text(text, strip_tashkeel=True)
        # Empty string cases
        empty_res = ArabicIndicNormalizer.normalize_text("")
        self.assertEqual(empty_res.map_span_to_original(0, 0), (0, 0))

        # Clamp cases
        self.assertEqual(res.map_span_to_original(-5, -1), (0, 0))
        self.assertEqual(res.map_span_to_original(100, 200), (len(text), len(text)))

    def test_complex_mena_pii_string(self):
        # Realistic Arabic sentence with mixed RTL/LTR, diacritics, and Eastern digits:
        # "المُواطِنُ أَحْمَد، رَقْمُ الهُوِيَّةِ الوَطَنِيَّةِ: ١٠٨٢٣٤٥٦٧٨ وتاريخ الميلاد ١٩٩٠/٠٥/١٢"
        text = "المُواطِنُ أَحْمَد، رَقْمُ الهُوِيَّةِ الوَطَنِيَّةِ: ١٠٨٢٣٤٥٦٧٨ وتاريخ الميلاد ١٩٩٠/٠٥/١٢"
        res = ArabicIndicNormalizer.normalize_text(
            text,
            strip_tashkeel=True,
            strip_tatweel=True,
            convert_digits=True,
        )

        # Locate normalized ID
        id_norm = "1082345678"
        self.assertIn(id_norm, res.normalized_text)
        n_start = res.normalized_text.index(id_norm)
        n_end = n_start + len(id_norm)

        # Map back to raw
        o_start, o_end = res.map_span_to_original(n_start, n_end)
        raw_slice = text[o_start:o_end]
        self.assertEqual(raw_slice, "١٠٨٢٣٤٥٦٧٨")


if __name__ == "__main__":
    unittest.main()
