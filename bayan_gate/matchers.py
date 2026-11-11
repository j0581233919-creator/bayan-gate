"""Algorithmic validators and regex matchers for MENA regional and universal PII.

Implements:
- ISO 7064 MOD 97-10 check for GCC and regional IBANs.
- ISO/IEC 7812-1 Luhn algorithm for credit cards, Saudi National IDs, and Iqamas.
- Structural validators for UAE Emirates ID and Egyptian National ID.
- Regional phone number validation (+966, +971, +20, +965, +974, +973, +968).
- Email and IP address regex matchers.
"""

from __future__ import annotations
import calendar
import datetime
import re
from typing import Any, Dict, List, Optional, Tuple

from .models import EntityType


# ---------------------------------------------------------------------------
# 1. Algorithmic Checksum Validators
# ---------------------------------------------------------------------------

def validate_luhn(digits_str: str) -> bool:
    """Validates the standard Luhn (mod-10) checksum algorithm.

    Used by Credit Cards, Saudi National IDs, and Saudi Iqamas.
    """
    clean_digits = [int(c) for c in digits_str if c.isdigit()]
    if len(clean_digits) < 2:
        return False

    checksum = 0
    reverse_digits = clean_digits[::-1]

    for idx, d in enumerate(reverse_digits):
        if idx % 2 == 1:
            doubled = d * 2
            checksum += doubled if doubled < 10 else (doubled - 9)
        else:
            checksum += d

    return checksum % 10 == 0


# GCC & Regional IBAN standard lengths
GCC_IBAN_LENGTHS = {
    "SA": 24,  # Saudi Arabia
    "AE": 23,  # United Arab Emirates
    "EG": 29,  # Egypt
    "KW": 30,  # Kuwait
    "QA": 29,  # Qatar
    "BH": 22,  # Bahrain
    "OM": 23,  # Oman
    "JO": 30,  # Jordan
}

GCC_COUNTRY_NAMES = {
    "SA": "Saudi Arabia",
    "AE": "United Arab Emirates",
    "EG": "Egypt",
    "KW": "Kuwait",
    "QA": "Qatar",
    "BH": "Bahrain",
    "OM": "Oman",
    "JO": "Jordan",
}


def validate_iban(iban_str: str) -> Tuple[bool, Optional[str], Dict[str, Any]]:
    """Validates an IBAN using the ISO 7064 MOD 97-10 algorithm.

    Returns:
        (is_valid, country_code, metadata)
    """
    clean = re.sub(r"[\s-]+", "", iban_str).upper()
    if len(clean) < 15 or len(clean) > 34:
        return False, None, {}

    country_code = clean[:2]
    if not country_code.isalpha():
        return False, None, {}

    # Length check for known GCC/regional countries
    expected_len = GCC_IBAN_LENGTHS.get(country_code)
    if expected_len and len(clean) != expected_len:
        return False, country_code, {"error": f"Invalid length for {country_code} IBAN (expected {expected_len}, got {len(clean)})"}

    # Move first 4 characters to the end
    rearranged = clean[4:] + clean[:4]

    # Replace letters with two-digit numbers (A=10, ..., Z=35)
    numeric_chars = []
    for ch in rearranged:
        if ch.isdigit():
            numeric_chars.append(ch)
        elif ch.isalpha():
            numeric_chars.append(str(ord(ch) - ord("A") + 10))
        else:
            return False, country_code, {"error": "Invalid character in IBAN"}

    numeric_str = "".join(numeric_chars)

    # MOD 97-10 calculation
    try:
        mod_result = int(numeric_str) % 97
        is_valid = (mod_result == 1)
    except Exception:
        return False, country_code, {"error": "Numeric conversion error"}

    meta = {
        "country_code": country_code,
        "country_name": GCC_COUNTRY_NAMES.get(country_code, "International"),
        "formatted_iban": clean,
        "is_gcc": country_code in GCC_IBAN_LENGTHS,
    }
    return is_valid, country_code, meta


# ---------------------------------------------------------------------------
# 2. Regional Identity Document Validators
# ---------------------------------------------------------------------------

def validate_saudi_national_id_or_iqama(id_str: str) -> Tuple[bool, EntityType, Dict[str, Any]]:
    """Validates Saudi National ID (starts with 1) or Iqama (starts with 2).

    Structure: 10 digits, Luhn checksum.
    """
    clean = re.sub(r"[\s-]+", "", id_str)
    if len(clean) != 10 or not clean.isdigit():
        return False, EntityType.SAUDI_NATIONAL_ID, {}

    first_digit = clean[0]
    if first_digit == "1":
        entity_type = EntityType.SAUDI_NATIONAL_ID
        id_type = "citizen"
    elif first_digit == "2":
        entity_type = EntityType.SAUDI_IQAMA
        id_type = "resident"
    else:
        return False, EntityType.SAUDI_NATIONAL_ID, {}

    checksum_ok = validate_luhn(clean)

    meta = {
        "id_type": id_type,
        "country": "SA",
        "first_digit": first_digit,
        "is_valid_checksum": checksum_ok,
    }
    return True, entity_type, meta


def validate_uae_emirates_id(id_str: str) -> Tuple[bool, Dict[str, Any]]:
    """Validates UAE Emirates ID.

    Format: 784-YYYY-XXXXXXX-Z (15 digits).
    Starts with 784, birth year YYYY between 1900 and 2099.
    """
    clean = re.sub(r"[\s-]+", "", id_str)
    if len(clean) != 15 or not clean.isdigit():
        return False, {}

    if not clean.startswith("784"):
        return False, {}

    year_str = clean[3:7]
    try:
        year = int(year_str)
        max_year = datetime.date.today().year + 1
        if not (1900 <= year <= max_year):
            return False, {}
    except ValueError:
        return False, {}

    formatted = f"{clean[:3]}-{clean[3:7]}-{clean[7:14]}-{clean[14]}"

    meta = {
        "country": "AE",
        "birth_year": year,
        "serial_number": clean[7:14],
        "check_digit": clean[14],
        "formatted": formatted,
    }
    return True, meta


EGYPT_GOVERNORATES = {
    "01": "Cairo", "02": "Alexandria", "03": "Port Said", "04": "Suez",
    "11": "Damietta", "12": "Dakahlia", "13": "Ash Sharqia", "14": "Al Qalyubia",
    "15": "Kafr El Sheikh", "16": "Gharbia", "17": "Monufia", "18": "El Beheira",
    "19": "Ismailia", "21": "Giza", "22": "Beni Suef", "23": "Faiyum",
    "24": "Minya", "25": "Asyut", "26": "Sohag", "27": "Qena", "28": "Aswan",
    "29": "Luxor", "31": "Red Sea", "32": "New Valley", "33": "Matrouh",
    "34": "North Sinai", "35": "South Sinai", "88": "Citizens Born Abroad",
}


def validate_egyptian_national_id(id_str: str) -> Tuple[bool, Dict[str, Any]]:
    """Validates Egyptian National ID.

    Format: 14 digits: CYYMMDDSSNNNC
    - C: Century (2 for 1900-1999, 3 for 2000-2099)
    - YYMMDD: Birth Date
    - SS: Governorate Code
    - NNN: Sequence Number (odd=male, even=female)
    - C: Check digit
    """
    clean = re.sub(r"[\s-]+", "", id_str)
    if len(clean) != 14 or not clean.isdigit():
        return False, {}

    century_digit = clean[0]
    if century_digit == "2":
        century_base = 1900
    elif century_digit == "3":
        century_base = 2000
    else:
        return False, {}

    yy = int(clean[1:3])
    mm = int(clean[3:5])
    dd = int(clean[5:7])

    year = century_base + yy

    # Validate Gregorian birthdate
    if not (1 <= mm <= 12):
        return False, {}

    max_days = calendar.monthrange(year, mm)[1]
    if not (1 <= dd <= max_days):
        return False, {}

    gov_code = clean[7:9]
    gov_name = EGYPT_GOVERNORATES.get(gov_code, "Unknown Governorate")

    seq = int(clean[9:13])
    gender = "Male" if (seq % 2 == 1) else "Female"

    meta = {
        "country": "EG",
        "birth_date": f"{year:04d}-{mm:02d}-{dd:02d}",
        "governorate_code": gov_code,
        "governorate_name": gov_name,
        "gender": gender,
    }
    return True, meta


# ---------------------------------------------------------------------------
# 3. Credit Card Network Detection & Validation
# ---------------------------------------------------------------------------

def validate_credit_card(card_str: str) -> Tuple[bool, Dict[str, Any]]:
    """Validates payment card using Luhn algorithm and identifies card network."""
    clean = re.sub(r"[\s-]+", "", card_str)
    if not (13 <= len(clean) <= 19) or not clean.isdigit():
        return False, {}

    luhn_ok = validate_luhn(clean)
    if not luhn_ok:
        return False, {}

    # Network identification
    network = "Unknown"
    if clean.startswith("4"):
        network = "Visa"
    elif re.match(r"^(?:5[1-5]|222[1-9]|22[3-9]\d|2[3-6]\d{2}|27[01]\d|2720)", clean):
        network = "Mastercard"
    elif clean.startswith(("34", "37")):
        network = "American Express"
    elif clean.startswith(("6011", "65", "644", "645")):
        network = "Discover"

    meta = {
        "network": network,
        "length": len(clean),
        "last_four": clean[-4:],
        "is_valid_checksum": True,
    }
    return True, meta


# ---------------------------------------------------------------------------
# 4. Regional Phone Number Detection
# ---------------------------------------------------------------------------

REGIONAL_PHONE_PATTERNS = [
    # Saudi Arabia: +966 5X XXX XXXX, 00966 5X..., 05XXXXXXXX
    (re.compile(r"(?:(?:\+?966|00966)5\d{8}|05\d{8})\b"), "SA", "Saudi Arabia"),
    # UAE: +971 5X XXX XXXX, 00971 5X..., 05XXXXXXXX
    (re.compile(r"(?:(?:\+?971|00971)5\d{8}|05\d{8})\b"), "AE", "United Arab Emirates"),
    # Egypt: +20 1X XXXX XXXX, 0020 1X..., 01[0125]XXXXXXXX
    (re.compile(r"(?:(?:\+?20|0020)1[0125]\d{8}|01[0125]\d{8})\b"), "EG", "Egypt"),
    # Kuwait: +965 [569]\d{7}
    (re.compile(r"(?:(?:\+?965|00965)[569]\d{7})\b"), "KW", "Kuwait"),
    # Qatar: +974 [3567]\d{7}
    (re.compile(r"(?:(?:\+?974|00974)[3567]\d{7})\b"), "QA", "Qatar"),
    # Bahrain: +973 [36]\d{7}
    (re.compile(r"(?:(?:\+?973|00973)[36]\d{7})\b"), "BH", "Bahrain"),
    # Oman: +968 [79]\d{7}
    (re.compile(r"(?:(?:\+?968|00968)[79]\d{7})\b"), "OM", "Oman"),
]


def validate_regional_phone(phone_str: str) -> Tuple[bool, Dict[str, Any]]:
    """Validates phone number and maps country metadata."""
    clean = re.sub(r"[\s()-]+", "", phone_str)
    if len(clean) < 8 or len(clean) > 16:
        return False, {}

    for pattern, country_code, country_name in REGIONAL_PHONE_PATTERNS:
        if pattern.fullmatch(clean):
            return True, {
                "country_code": country_code,
                "country_name": country_name,
                "clean_number": clean,
            }

    # Generic international E.164 phone number (must start with '+')
    if clean.startswith("+") and re.fullmatch(r"\+[1-9]\d{7,14}", clean):
        return True, {
            "country_code": "INTL",
            "country_name": "International",
            "clean_number": clean,
        }

    return False, {}


# ---------------------------------------------------------------------------
# 5. Email & IP Regex Validators
# ---------------------------------------------------------------------------

EMAIL_REGEX = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)

IPV4_REGEX = re.compile(
    r"\b(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(?:\.(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}\b"
)

IPV6_REGEX = re.compile(
    r"\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b|"
    r"\b(?:[0-9a-fA-F]{1,4}:){1,7}:|"
    r"\b:(?::[0-9a-fA-F]{1,4}){1,7}\b"
)
