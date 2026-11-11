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
from .demo import run_demo

_default_engine = RegionalPIIEngine()
_default_redactor = PIIRedactor(engine=_default_engine)


def detect(
    text: str,
    enabled_types=None,
    min_confidence: float = 0.5,
):
    """Detects sensitive entities in text with exact character offset grounding."""
    return _default_engine.detect(
        text,
        enabled_types=enabled_types,
        min_confidence=min_confidence,
    )


def redact(
    text: str,
    policy: MaskingPolicy = MaskingPolicy.REDACT_FULL,
    enabled_types=None,
    min_confidence: float = 0.5,
    custom_replacer=None,
) -> RedactionResult:
    """Redacts sensitive PII from text according to policy."""
    return _default_redactor.redact(
        text,
        policy=policy,
        enabled_types=enabled_types,
        min_confidence=min_confidence,
        custom_replacer=custom_replacer,
    )


def stream_redact(
    in_stream,
    out_stream,
    policy: MaskingPolicy = MaskingPolicy.REDACT_FULL,
    enabled_types=None,
    min_confidence: float = 0.5,
):
    """Streams lines from in_stream, redacts PII, and writes to out_stream."""
    for line in in_stream:
        res = _default_redactor.redact(
            line,
            policy=policy,
            enabled_types=enabled_types,
            min_confidence=min_confidence,
        )
        out_stream.write(res.redacted_text)


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
    "detect",
    "redact",
    "stream_redact",
    "run_demo",
]
