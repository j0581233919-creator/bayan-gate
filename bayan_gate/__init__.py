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
]
