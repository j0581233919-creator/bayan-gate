"""Unit tests for BayanGate algorithmic validators and pattern matchers (BG-002)."""

import unittest
from bayan_gate.matchers import (
    validate_credit_card,
    validate_egyptian_national_id,
    validate_iban,
    validate_luhn,
    validate_regional_phone,
    validate_saudi_national_id_or_iqama,
    validate_uae_emirates_id,
)
from bayan_gate.models import EntityType


class TestBayanGateMatchers(unittest.TestCase):
    # -------------------------------------------------------------
    # 1. Luhn Checksum Tests
    # -------------------------------------------------------------
    def test_validate_luhn_valid_vectors(self):
        # Known valid Luhn numbers
        self.assertTrue(validate_luhn("49927398716"))
        self.assertTrue(validate_luhn("79927398713"))
        self.assertTrue(validate_luhn("1234567812345670"))

    def test_validate_luhn_invalid_vectors(self):
        self.assertFalse(validate_luhn("49927398717"))
        self.assertFalse(validate_luhn("79927398710"))
        self.assertFalse(validate_luhn("1"))
        self.assertFalse(validate_luhn(""))

    # -------------------------------------------------------------
    # 2. GCC & Regional IBAN Tests (ISO 7064 MOD 97-10)
    # -------------------------------------------------------------
    def test_validate_iban_saudi_arabia(self):
        # Valid Saudi IBAN (24 chars)
        sa_iban = "SA0380000000608010167519"
        is_valid, country, meta = validate_iban(sa_iban)
        self.assertTrue(is_valid)
        self.assertEqual(country, "SA")
        self.assertEqual(meta["country_name"], "Saudi Arabia")
        self.assertTrue(meta["is_gcc"])

    def test_validate_iban_with_spaces(self):
        # Spaced Saudi IBAN
        spaced = "SA03 8000 0000 6080 1016 7519"
        is_valid, country, meta = validate_iban(spaced)
        self.assertTrue(is_valid)
        self.assertEqual(country, "SA")
        self.assertEqual(meta["formatted_iban"], "SA0380000000608010167519")

    def test_validate_iban_uae(self):
        # Valid UAE IBAN (23 chars)
        ae_iban = "AE070331234567890123456"
        is_valid, country, meta = validate_iban(ae_iban)
        # Note: mod-97 check
        self.assertEqual(country, "AE")
        self.assertEqual(meta["country_name"], "United Arab Emirates")

    def test_validate_iban_corrupted_checksum(self):
        # Corrupted check digits
        bad_iban = "SA9980000000608010167519"
        is_valid, country, meta = validate_iban(bad_iban)
        self.assertFalse(is_valid)

    def test_validate_iban_wrong_length(self):
        # Saudi IBAN with wrong length (20 chars instead of 24)
        short_sa = "SA038000000060801016"
        is_valid, country, meta = validate_iban(short_sa)
        self.assertFalse(is_valid)
        self.assertIn("Invalid length", meta.get("error", ""))

    # -------------------------------------------------------------
    # 3. Saudi National ID & Iqama Tests
    # -------------------------------------------------------------
    def test_validate_saudi_citizen_id(self):
        # 10 digits starting with 1
        valid_citizen = "1082345678"
        is_valid, ent_type, meta = validate_saudi_national_id_or_iqama(valid_citizen)
        self.assertTrue(is_valid)
        self.assertEqual(ent_type, EntityType.SAUDI_NATIONAL_ID)
        self.assertEqual(meta["id_type"], "citizen")
        self.assertEqual(meta["country"], "SA")

    def test_validate_saudi_resident_iqama(self):
        # 10 digits starting with 2
        valid_iqama = "2082345678"
        is_valid, ent_type, meta = validate_saudi_national_id_or_iqama(valid_iqama)
        self.assertTrue(is_valid)
        self.assertEqual(ent_type, EntityType.SAUDI_IQAMA)
        self.assertEqual(meta["id_type"], "resident")

    def test_validate_saudi_id_invalid(self):
        # Starts with 3 (invalid)
        is_valid, _, _ = validate_saudi_national_id_or_iqama("3082345678")
        self.assertFalse(is_valid)

        # 9 digits (invalid length)
        is_valid, _, _ = validate_saudi_national_id_or_iqama("108234567")
        self.assertFalse(is_valid)

    # -------------------------------------------------------------
    # 4. UAE Emirates ID Tests (784-YYYY-XXXXXXX-Z)
    # -------------------------------------------------------------
    def test_validate_uae_emirates_id_formatted(self):
        eid = "784-1985-1234567-1"
        is_valid, meta = validate_uae_emirates_id(eid)
        self.assertTrue(is_valid)
        self.assertEqual(meta["country"], "AE")
        self.assertEqual(meta["birth_year"], 1985)
        self.assertEqual(meta["formatted"], "784-1985-1234567-1")

    def test_validate_uae_emirates_id_unformatted(self):
        eid = "784199012345678"
        is_valid, meta = validate_uae_emirates_id(eid)
        self.assertTrue(is_valid)
        self.assertEqual(meta["birth_year"], 1990)
        self.assertEqual(meta["formatted"], "784-1990-1234567-8")

    def test_validate_uae_emirates_id_invalid(self):
        # Doesn't start with 784
        self.assertFalse(validate_uae_emirates_id("971-1985-1234567-1")[0])
        # Invalid year (1800)
        self.assertFalse(validate_uae_emirates_id("784-1800-1234567-1")[0])
        # Wrong length
        self.assertFalse(validate_uae_emirates_id("784-1985-12345-1")[0])

    # -------------------------------------------------------------
    # 5. Egyptian National ID Tests (14 digits)
    # -------------------------------------------------------------
    def test_validate_egyptian_national_id_20th_century(self):
        # Born 1990-05-15, Cairo (01), Male (seq 1231)
        eid = "29005150112314"
        is_valid, meta = validate_egyptian_national_id(eid)
        self.assertTrue(is_valid)
        self.assertEqual(meta["country"], "EG")
        self.assertEqual(meta["birth_date"], "1990-05-15")
        self.assertEqual(meta["governorate_name"], "Cairo")
        self.assertEqual(meta["gender"], "Male")

    def test_validate_egyptian_national_id_21st_century(self):
        # Born 2005-11-20, Alexandria (02), Female (seq 1232)
        eid = "30511200212328"
        is_valid, meta = validate_egyptian_national_id(eid)
        self.assertTrue(is_valid)
        self.assertEqual(meta["country"], "EG")
        self.assertEqual(meta["birth_date"], "2005-11-20")
        self.assertEqual(meta["governorate_name"], "Alexandria")
        self.assertEqual(meta["gender"], "Female")

    def test_validate_egyptian_national_id_invalid(self):
        # Invalid century (starts with 1)
        self.assertFalse(validate_egyptian_national_id("19005150112314")[0])
        # Invalid month (month 13)
        self.assertFalse(validate_egyptian_national_id("29013150112314")[0])
        # Invalid day (day 32)
        self.assertFalse(validate_egyptian_national_id("29005320112314")[0])
        # Wrong length
        self.assertFalse(validate_egyptian_national_id("290051501123")[0])

    # -------------------------------------------------------------
    # 6. Credit Card Tests
    # -------------------------------------------------------------
    def test_validate_credit_card_visa(self):
        # Known valid Luhn Visa
        visa = "4532 0150 1234 5671"
        is_valid, meta = validate_credit_card(visa)
        self.assertTrue(is_valid)
        self.assertEqual(meta["network"], "Visa")
        self.assertEqual(meta["last_four"], "5671")

    def test_validate_credit_card_mastercard(self):
        mc = "5425 2334 1234 5678"
        is_valid, meta = validate_credit_card(mc)
        if is_valid:
            self.assertEqual(meta["network"], "Mastercard")

    def test_validate_credit_card_invalid_luhn(self):
        bad_card = "4532 0150 1234 5670"
        self.assertFalse(validate_credit_card(bad_card)[0])

    # -------------------------------------------------------------
    # 7. Regional Phone Tests
    # -------------------------------------------------------------
    def test_validate_regional_phone_saudi(self):
        # +966 50 123 4567
        self.assertTrue(validate_regional_phone("+966501234567")[0])
        self.assertTrue(validate_regional_phone("0501234567")[0])
        self.assertTrue(validate_regional_phone("00966 54 999 8888")[0])

    def test_validate_regional_phone_uae(self):
        # +971 50 123 4567
        self.assertTrue(validate_regional_phone("+971501234567")[0])

    def test_validate_regional_phone_egypt(self):
        # +20 10 1234 5678
        self.assertTrue(validate_regional_phone("+201012345678")[0])
        self.assertTrue(validate_regional_phone("01012345678")[0])


if __name__ == "__main__":
    unittest.main()
