"""BayanGate Redactor Engine and Masking Policies.

Implements:
- PIIRedactor: High-precision redaction, masking, and pseudonymization engine.
- Reverse character offset replacement guaranteeing zero offset drift across mixed RTL/LTR text.
- Masking policies: REDACT_FULL, MASK_PARTIAL, PSEUDONYMIZE_HASH, and REPLACE_SYNTHETIC.
- Salted deterministic pseudonymization with format-preserving prefixes.
- Cryptographic tamper-evident audit hashes without logging sensitive data.
"""

from __future__ import annotations
import hashlib
import hmac
import re
from typing import Any, Callable, Dict, List, Optional, Set

from .models import EntityType, MaskingPolicy, PIISpan, RedactionResult
from .engine import RegionalPIIEngine


class PIIRedactor:
    """Configurable PII redaction and masking engine."""

    def __init__(
        self,
        engine: Optional[RegionalPIIEngine] = None,
        salt: Optional[str] = None,
        mask_char: str = "*",
    ):
        """Initializes the PIIRedactor.

        Args:
            engine: Optional RegionalPIIEngine instance. Defaults to a new RegionalPIIEngine.
            salt: Secret salt for deterministic pseudonymization (PSEUDONYMIZE_HASH).
            mask_char: Character used for partial masking (default: '*').
        """
        self.engine = engine or RegionalPIIEngine()
        self.salt = salt or "BayanGate-Default-Deterministic-Salt-2026"
        self.mask_char = mask_char

    def redact(
        self,
        text: str,
        policy: MaskingPolicy = MaskingPolicy.REDACT_FULL,
        enabled_types: Optional[Set[EntityType]] = None,
        min_confidence: Optional[float] = None,
        custom_replacer: Optional[Callable[[PIISpan], str]] = None,
        salt: Optional[str] = None,
    ) -> RedactionResult:
        """Detects sensitive entities and applies the specified redaction policy.

        Args:
            text: Input text containing potential sensitive PII.
            policy: MaskingPolicy to apply.
            enabled_types: Set of EntityType categories to detect and redact.
            min_confidence: Confidence threshold for entity detection.
            custom_replacer: Optional callable (PIISpan) -> str for custom replacement strings.
            salt: Optional per-call HMAC salt override.

        Returns:
            RedactionResult containing the redacted text, detected spans, and audit hash.
        """
        if not text:
            return RedactionResult(
                original_length=0,
                redacted_text="",
                entities_detected=[],
                policy_applied=policy,
                audit_hash=self._compute_audit_hash("", "", 0),
            )

        spans = self.engine.detect(
            text,
            enabled_types=enabled_types,
            min_confidence=min_confidence,
        )

        return self.redact_spans(
            text,
            spans,
            policy=policy,
            custom_replacer=custom_replacer,
            salt=salt,
        )

    def redact_spans(
        self,
        text: str,
        spans: List[PIISpan],
        policy: MaskingPolicy = MaskingPolicy.REDACT_FULL,
        custom_replacer: Optional[Callable[[PIISpan], str]] = None,
        salt: Optional[str] = None,
    ) -> RedactionResult:
        """Applies redaction transformations to a pre-computed list of PIISpans.

        Replaces spans in descending order of character offsets (right to left)
        to guarantee zero offset distortion of preceding spans.
        """
        if not spans:
            return RedactionResult(
                original_length=len(text),
                redacted_text=text,
                entities_detected=[],
                policy_applied=policy,
                audit_hash=self._compute_audit_hash(text, text, 0),
            )

        # Sort descending by start_char for safe reverse replacement
        sorted_spans = sorted(spans, key=lambda s: s.start_char, reverse=True)

        chars = list(text)
        for span in sorted_spans:
            replacement = self._generate_replacement(span, policy, custom_replacer, salt=salt)
            # Replace slice [start_char:end_char] with replacement string
            chars[span.start_char:span.end_char] = list(replacement)

        redacted_str = "".join(chars)
        audit_hash = self._compute_audit_hash(text, redacted_str, len(spans))

        # Return original spans sorted ascending by start_char
        ascending_spans = sorted(spans, key=lambda s: s.start_char)

        return RedactionResult(
            original_length=len(text),
            redacted_text=redacted_str,
            entities_detected=ascending_spans,
            policy_applied=policy,
            audit_hash=audit_hash,
        )

    # -----------------------------------------------------------------------
    # Replacement Generators
    # -----------------------------------------------------------------------

    def _generate_replacement(
        self,
        span: PIISpan,
        policy: MaskingPolicy,
        custom_replacer: Optional[Callable[[PIISpan], str]] = None,
        salt: Optional[str] = None,
    ) -> str:
        """Generates replacement string according to policy."""
        if custom_replacer is not None:
            return custom_replacer(span)

        if policy == MaskingPolicy.REDACT_FULL:
            return f"[REDACTED_{span.entity_type.value}]"

        if policy == MaskingPolicy.MASK_PARTIAL:
            return self._mask_partial(span)

        if policy == MaskingPolicy.PSEUDONYMIZE_HASH:
            return self._pseudonymize_hash(span, salt=salt)

        if policy == MaskingPolicy.REPLACE_SYNTHETIC:
            return self._replace_synthetic(span)

        # Default fallback
        return f"[REDACTED_{span.entity_type.value}]"

    def _mask_partial(self, span: PIISpan) -> str:
        """Applies partial masking preserving format, delimiters, and surrounding digits."""
        raw = span.raw_text
        ent = span.entity_type
        m_char = self.mask_char

        # 1. Email Address: keep first char of username and full domain
        if ent == EntityType.EMAIL_ADDRESS and "@" in raw:
            user, domain = raw.split("@", 1)
            if len(user) <= 1:
                masked_user = m_char
            elif len(user) <= 3:
                masked_user = user[0] + (m_char * (len(user) - 1))
            else:
                masked_user = user[0] + (m_char * (len(user) - 2)) + user[-1]
            return f"{masked_user}@{domain}"

        # 2. GCC IBAN: preserve country code & check digits (first 4) and last 4
        if ent == EntityType.GCC_IBAN:
            # Mask inner alphanumeric characters while preserving spaces
            chars = list(raw)
            # Find indices of non-space chars
            non_space = [i for i, c in enumerate(chars) if not c.isspace()]
            if len(non_space) > 8:
                # Mask from index 4 to len - 4
                for idx in non_space[4:-4]:
                    chars[idx] = m_char
                return "".join(chars)

        # 3. Credit Card: preserve first 4 and last 4, mask middle digits and preserve spaces/dashes
        if ent == EntityType.CREDIT_CARD:
            chars = list(raw)
            digit_indices = [i for i, c in enumerate(chars) if c.isdigit()]
            if len(digit_indices) > 8:
                for idx in digit_indices[4:-4]:
                    chars[idx] = m_char
                return "".join(chars)

        # 4. UAE Emirates ID (15 digits): preserve 784 and last 1 or 2 digits
        if ent == EntityType.UAE_NATIONAL_ID:
            chars = list(raw)
            digit_indices = [i for i, c in enumerate(chars) if c.isdigit() or ord("٠") <= ord(c) <= ord("٩")]
            if len(digit_indices) >= 15:
                # Keep first 3 (784) and last 1, mask middle
                for idx in digit_indices[3:-1]:
                    chars[idx] = m_char
                return "".join(chars)

        # 5. Egyptian National ID (14 digits): keep first 3 and last 3
        if ent == EntityType.EGYPTIAN_NATIONAL_ID:
            chars = list(raw)
            digit_indices = [i for i, c in enumerate(chars) if c.isdigit() or ord("٠") <= ord(c) <= ord("٩")]
            if len(digit_indices) >= 14:
                for idx in digit_indices[3:-3]:
                    chars[idx] = m_char
                return "".join(chars)

        # 6. Saudi National ID & Iqama (10 digits): keep first 3 and last 3
        if ent in (EntityType.SAUDI_NATIONAL_ID, EntityType.SAUDI_IQAMA):
            chars = list(raw)
            digit_indices = [i for i, c in enumerate(chars) if c.isdigit() or ord("٠") <= ord(c) <= ord("٩")]
            if len(digit_indices) >= 10:
                for idx in digit_indices[3:-3]:
                    chars[idx] = m_char
                return "".join(chars)

        # 7. Phone Number: keep prefix/country code and last 2 digits
        if ent == EntityType.PHONE_NUMBER:
            chars = list(raw)
            digit_indices = [i for i, c in enumerate(chars) if c.isdigit() or ord("٠") <= ord(c) <= ord("٩")]
            if len(digit_indices) >= 7:
                # Keep first 3 digits and last 2 digits
                for idx in digit_indices[3:-2]:
                    chars[idx] = m_char
                return "".join(chars)

        # 8. IP Address: mask host part
        if ent == EntityType.IP_ADDRESS and "." in raw:
            parts = raw.split(".")
            if len(parts) == 4:
                return f"{parts[0]}.{parts[1]}.{m_char * len(parts[2])}.{m_char * len(parts[3])}"

        # Generic Fallback: mask middle 50% of string
        if len(raw) <= 4:
            return m_char * len(raw)
        keep = max(1, len(raw) // 4)
        return raw[:keep] + (m_char * (len(raw) - 2 * keep)) + raw[-keep:]

    def _pseudonymize_hash(self, span: PIISpan, salt: Optional[str] = None) -> str:
        """Generates deterministic keyed HMAC pseudonym token."""
        effective_salt = salt if salt is not None else self.salt
        msg = f"{span.entity_type.value}:{span.normalized_text}".encode("utf-8")
        h = hmac.new(effective_salt.encode("utf-8"), msg, hashlib.sha256).hexdigest()[:8]

        prefix_map = {
            EntityType.SAUDI_NATIONAL_ID: "SA_ID",
            EntityType.SAUDI_IQAMA: "SA_IQAMA",
            EntityType.UAE_NATIONAL_ID: "EID",
            EntityType.EGYPTIAN_NATIONAL_ID: "EG_ID",
            EntityType.GCC_IBAN: "IBAN",
            EntityType.CREDIT_CARD: "CARD",
            EntityType.PHONE_NUMBER: "TEL",
            EntityType.EMAIL_ADDRESS: "EMAIL",
            EntityType.IP_ADDRESS: "IP",
        }
        prefix = prefix_map.get(span.entity_type, "TOKEN")
        return f"[{prefix}_{h}]"

    def _replace_synthetic(self, span: PIISpan) -> str:
        """Generates realistic synthetic replacement preserving structure and country."""
        ent = span.entity_type
        if ent == EntityType.SAUDI_NATIONAL_ID:
            return "1999999999"
        if ent == EntityType.SAUDI_IQAMA:
            return "2999999999"
        if ent == EntityType.UAE_NATIONAL_ID:
            return "784-1990-0000000-1"
        if ent == EntityType.EGYPTIAN_NATIONAL_ID:
            return "29001010100001"
        if ent == EntityType.GCC_IBAN:
            country = span.metadata.get("country_code", "SA")
            return f"{country}0000000000000000000000"[:len(span.raw_text)]
        if ent == EntityType.CREDIT_CARD:
            return "4000000000000000"
        if ent == EntityType.PHONE_NUMBER:
            country = span.metadata.get("country_code", "SA")
            if country == "SA":
                return "0500000000"
            if country == "AE":
                return "0500000000"
            if country == "EG":
                return "01000000000"
            return "+966500000000"
        if ent == EntityType.EMAIL_ADDRESS:
            return "redacted-user@example.com"
        if ent == EntityType.IP_ADDRESS:
            return "10.0.0.1"

        return f"[SYNTHETIC_{ent.value}]"

    @staticmethod
    def _compute_audit_hash(original: str, redacted: str, count: int) -> str:
        """Computes tamper-evident SHA-256 audit digest over redaction transformation."""
        hasher = hashlib.sha256()
        hasher.update(original.encode("utf-8"))
        hasher.update(b"::")
        hasher.update(redacted.encode("utf-8"))
        hasher.update(b"::")
        hasher.update(str(count).encode("utf-8"))
        return hasher.hexdigest()
