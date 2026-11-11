"""BayanGate: Arabic & MENA Sensitive Data Recognition and Privacy-Safe Redaction SDK."""

__version__ = "0.1.0"

from .models import (
    EntityType,
    MaskingPolicy,
    PIISpan,
    RedactionResult,
)
from .normalizer import (
    ArabicIndicNormalizer,
    NormalizedText,
    EASTERN_ARABIC_INDIC_DIGITS,
    EXTENDED_ARABIC_INDIC_DIGITS,
    WESTERN_ARABIC_DIGITS,
)
from .matchers import (
    validate_luhn,
    validate_iban,
    validate_saudi_national_id_or_iqama,
    validate_uae_emirates_id,
    validate_egyptian_national_id,
    validate_credit_card,
    validate_regional_phone,
)
from .engine import RegionalPIIEngine
from .redactor import PIIRedactor

__all__ = [
    "EntityType",
    "MaskingPolicy",
    "PIISpan",
    "RedactionResult",
    "ArabicIndicNormalizer",
    "NormalizedText",
    "EASTERN_ARABIC_INDIC_DIGITS",
    "EXTENDED_ARABIC_INDIC_DIGITS",
    "WESTERN_ARABIC_DIGITS",
    "validate_luhn",
    "validate_iban",
    "validate_saudi_national_id_or_iqama",
    "validate_uae_emirates_id",
    "validate_egyptian_national_id",
    "validate_credit_card",
    "validate_regional_phone",
    "RegionalPIIEngine",
    "PIIRedactor",
]
