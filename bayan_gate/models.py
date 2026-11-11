"""Core data models for BayanGate sensitive data recognition and redaction.

Defines:
- EntityType: Enumeration of supported MENA regional and universal PII categories.
- MaskingPolicy: Redaction, masking, and pseudonymization policy options.
- PIISpan: Grounded detection record with exact character offsets in original unicode text.
- RedactionResult: Immutable container of redacted text, detection metadata, and audit summary.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class EntityType(str, Enum):
    """Supported sensitive entity categories with MENA regional prioritization."""
    # Regional Identity Documents
    SAUDI_NATIONAL_ID = "SAUDI_NATIONAL_ID"      # 10 digits starting with 1
    SAUDI_IQAMA = "SAUDI_IQAMA"                  # 10 digits starting with 2
    UAE_NATIONAL_ID = "UAE_NATIONAL_ID"          # Emirates ID: 15 digits (784-YYYY-XXXXXXX-Z)
    EGYPTIAN_NATIONAL_ID = "EGYPTIAN_NATIONAL_ID"# 14 digits with century/birthdate encoding

    # Financial Identifiers
    GCC_IBAN = "GCC_IBAN"                        # Saudi, UAE, Kuwait, Qatar, Bahrain, Oman, Egypt IBAN
    CREDIT_CARD = "CREDIT_CARD"                  # Major payment cards (Visa, MC, Mada, Amex)

    # Contact & Digital Identifiers
    PHONE_NUMBER = "PHONE_NUMBER"                # MENA regional phone numbers (+966, +971, +20, etc.)
    EMAIL_ADDRESS = "EMAIL_ADDRESS"              # Standard and regional email formats
    IP_ADDRESS = "IP_ADDRESS"                    # IPv4 and IPv6 addresses

    # Demographic & Contextual
    DATE_OF_BIRTH = "DATE_OF_BIRTH"              # Gregorian and Hijri dates of birth
    PERSON_NAME = "PERSON_NAME"                  # Arabic and Latin person names
    CUSTOM = "CUSTOM"                            # User-defined regex or semantic patterns


class MaskingPolicy(str, Enum):
    """Policies governing how detected sensitive entities are transformed."""
    REDACT_FULL = "REDACT_FULL"            # Replace with category label, e.g. [REDACTED_SAUDI_NATIONAL_ID]
    MASK_PARTIAL = "MASK_PARTIAL"          # Obfuscate middle digits, e.g. 102****789
    PSEUDONYMIZE_HASH = "PSEUDONYMIZE_HASH"# Deterministic keyed HMAC/hash token, e.g. [ID_a4f9b2]
    REPLACE_SYNTHETIC = "REPLACE_SYNTHETIC"# Realistic synthetic replacement preserving format


@dataclass(frozen=True)
class PIISpan:
    """Represents a detected sensitive entity with exact character-level grounding.

    Attributes:
        entity_type: The classified PII category.
        raw_text: The exact substring as it appeared in the raw input text.
        normalized_text: Standardized representation (e.g. Western digits 0-9, stripped formatting).
        start_char: Zero-indexed start character offset in original input.
        end_char: Zero-indexed end character offset (exclusive) in original input.
        confidence: Detection confidence score between 0.0 and 1.0.
        metadata: Domain-specific attributes (e.g. country, birthdate, card network, format).
        is_valid_checksum: True if algorithmic checksum passed (e.g. Luhn, ISO 7064 Mod 97-10).
    """
    entity_type: EntityType
    raw_text: str
    normalized_text: str
    start_char: int
    end_char: int
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_valid_checksum: Optional[bool] = None

    def __post_init__(self):
        if self.start_char < 0:
            raise ValueError(f"start_char must be non-negative, got {self.start_char}")
        if self.end_char <= self.start_char:
            raise ValueError(f"end_char ({self.end_char}) must be greater than start_char ({self.start_char})")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence must be between 0.0 and 1.0, got {self.confidence}")

    @property
    def span_length(self) -> int:
        """Length of the detected span in characters."""
        return self.end_char - self.start_char

    def verify_grounding(self, original_text: str) -> bool:
        """Verifies that raw_text matches the slice in original_text exactly."""
        if self.end_char > len(original_text):
            return False
        return original_text[self.start_char:self.end_char] == self.raw_text

    def to_dict(self) -> Dict[str, Any]:
        """Serializes detection span to dictionary."""
        return {
            "entity_type": self.entity_type.value,
            "raw_text": self.raw_text,
            "normalized_text": self.normalized_text,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "span_length": self.span_length,
            "confidence": round(self.confidence, 4),
            "metadata": dict(self.metadata),
            "is_valid_checksum": self.is_valid_checksum,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PIISpan:
        """Constructs PIISpan from dictionary."""
        return cls(
            entity_type=EntityType(data["entity_type"]),
            raw_text=str(data["raw_text"]),
            normalized_text=str(data["normalized_text"]),
            start_char=int(data["start_char"]),
            end_char=int(data["end_char"]),
            confidence=float(data.get("confidence", 1.0)),
            metadata=dict(data.get("metadata", {})),
            is_valid_checksum=data.get("is_valid_checksum"),
        )


@dataclass(frozen=True)
class RedactionResult:
    """Immutable container of redaction operation results and audit metadata."""
    original_length: int
    redacted_text: str
    entities_detected: List[PIISpan]
    policy_applied: MaskingPolicy
    audit_hash: Optional[str] = None

    @property
    def redaction_count(self) -> int:
        """Total number of redacted entities."""
        return len(self.entities_detected)

    @property
    def entity_type_counts(self) -> Dict[str, int]:
        """Breakdown of detected entities by category."""
        counts: Dict[str, int] = {}
        for span in self.entities_detected:
            k = span.entity_type.value
            counts[k] = counts.get(k, 0) + 1
        return counts

    def to_dict(self, include_raw_spans: bool = False) -> Dict[str, Any]:
        """Serializes redaction result to dictionary.

        Args:
            include_raw_spans: If True, includes raw unredacted entity text.
                               Default is False to enforce zero sensitive logging.
        """
        spans_out = []
        for span in self.entities_detected:
            d = span.to_dict()
            if not include_raw_spans:
                # Privacy-safe redaction summary: redact the raw and normalized texts in audit log
                d["raw_text"] = f"[LENGTH_{span.span_length}]"
                d["normalized_text"] = f"[LENGTH_{len(span.normalized_text)}]"
            spans_out.append(d)

        return {
            "original_length": self.original_length,
            "redacted_length": len(self.redacted_text),
            "redaction_count": self.redaction_count,
            "policy_applied": self.policy_applied.value,
            "entity_type_counts": self.entity_type_counts,
            "entities": spans_out,
            "audit_hash": self.audit_hash,
        }
