"""BayanGate Regional PII Detection Engine.

Integrates:
- ArabicIndicNormalizer for seamless Eastern/Western numeral handling and Tashkeel/Tatweel stripping.
- Exact zero-drift unicode span coordinate mapping back to raw text.
- Algorithmic and structural validators for MENA regional and universal sensitive identifiers.
- Intelligent overlap resolution and confidence scoring.
"""

from __future__ import annotations
import re
from typing import Dict, List, Optional, Set, Tuple

from .models import EntityType, PIISpan
from .normalizer import ArabicIndicNormalizer, NormalizedText
from .matchers import (
    EMAIL_REGEX,
    IPV4_REGEX,
    IPV6_REGEX,
    validate_credit_card,
    validate_egyptian_national_id,
    validate_iban,
    validate_regional_phone,
    validate_saudi_national_id_or_iqama,
    validate_uae_emirates_id,
)


# Specificity priority for overlap resolution
PRIORITY_MAP: Dict[EntityType, int] = {
    EntityType.GCC_IBAN: 100,
    EntityType.CREDIT_CARD: 90,
    EntityType.UAE_NATIONAL_ID: 80,
    EntityType.EGYPTIAN_NATIONAL_ID: 80,
    EntityType.SAUDI_NATIONAL_ID: 70,
    EntityType.SAUDI_IQAMA: 70,
    EntityType.EMAIL_ADDRESS: 60,
    EntityType.IP_ADDRESS: 50,
    EntityType.PHONE_NUMBER: 40,
    EntityType.DATE_OF_BIRTH: 30,
    EntityType.PERSON_NAME: 20,
    EntityType.CUSTOM: 10,
}


class RegionalPIIEngine:
    """High-precision sensitive data detector optimized for Arabic and MENA regional text."""

    def __init__(self, default_min_confidence: float = 0.5):
        self.default_min_confidence = default_min_confidence

    def detect(
        self,
        text: str,
        enabled_types: Optional[Set[EntityType]] = None,
        min_confidence: Optional[float] = None,
    ) -> List[PIISpan]:
        """Detects sensitive entities with exact character offsets in raw input text.

        Args:
            text: Raw input string (can be mixed Arabic/English, Arabic-Indic numerals, etc.).
            enabled_types: Optional set of EntityType values to detect. If None, all are enabled.
            min_confidence: Confidence threshold between 0.0 and 1.0.

        Returns:
            List of detected PIISpan objects sorted by start_char ascending.
        """
        if not text or not text.strip():
            return []

        threshold = min_confidence if min_confidence is not None else self.default_min_confidence

        # 1. Normalize text for pattern matching while preserving coordinate maps
        norm_res = ArabicIndicNormalizer.normalize_text(
            text,
            strip_tashkeel=True,
            strip_tatweel=True,
            convert_digits=True,
        )
        norm_text = norm_res.normalized_text

        candidates: List[PIISpan] = []

        # -------------------------------------------------------------
        # A. GCC & Regional IBANs
        # -------------------------------------------------------------
        if self._is_enabled(EntityType.GCC_IBAN, enabled_types):
            # Matches IBAN with optional spaces
            iban_regex = re.compile(r"\b([A-Za-z]{2}\d{2}(?:[ \t]*[A-Za-z0-9]){11,30})\b")
            for m in iban_regex.finditer(norm_text):
                matched_str = m.group(1)
                is_valid, country, meta = validate_iban(matched_str)
                if is_valid:
                    span = self._build_span(
                        norm_res, text, m.start(), m.end(),
                        entity_type=EntityType.GCC_IBAN,
                        normalized_val=meta.get("formatted_iban", matched_str),
                        confidence=1.0,
                        metadata=meta,
                        is_valid_checksum=True,
                    )
                    if span:
                        candidates.append(span)

        # -------------------------------------------------------------
        # B. UAE Emirates ID (784-YYYY-XXXXXXX-Z)
        # -------------------------------------------------------------
        if self._is_enabled(EntityType.UAE_NATIONAL_ID, enabled_types):
            eid_regex = re.compile(r"\b(784[\s-]?\d{4}[\s-]?\d{7}[\s-]?\d)\b")
            for m in eid_regex.finditer(norm_text):
                matched_str = m.group(1)
                is_valid, meta = validate_uae_emirates_id(matched_str)
                if is_valid:
                    span = self._build_span(
                        norm_res, text, m.start(), m.end(),
                        entity_type=EntityType.UAE_NATIONAL_ID,
                        normalized_val=meta.get("formatted", matched_str),
                        confidence=0.99,
                        metadata=meta,
                    )
                    if span:
                        candidates.append(span)

        # -------------------------------------------------------------
        # C. Egyptian National ID (14 digits)
        # -------------------------------------------------------------
        if self._is_enabled(EntityType.EGYPTIAN_NATIONAL_ID, enabled_types):
            eg_regex = re.compile(r"\b([23]\d{13})\b")
            for m in eg_regex.finditer(norm_text):
                matched_str = m.group(1)
                is_valid, meta = validate_egyptian_national_id(matched_str)
                if is_valid:
                    span = self._build_span(
                        norm_res, text, m.start(), m.end(),
                        entity_type=EntityType.EGYPTIAN_NATIONAL_ID,
                        normalized_val=matched_str,
                        confidence=0.95,
                        metadata=meta,
                    )
                    if span:
                        candidates.append(span)

        # -------------------------------------------------------------
        # D. Saudi National ID & Iqama (10 digits starting with 1 or 2)
        # -------------------------------------------------------------
        sa_types = {EntityType.SAUDI_NATIONAL_ID, EntityType.SAUDI_IQAMA}
        if enabled_types is None or sa_types.intersection(enabled_types):
            sa_regex = re.compile(r"\b([12]\d{9})\b")
            for m in sa_regex.finditer(norm_text):
                matched_str = m.group(1)
                is_valid, ent_type, meta = validate_saudi_national_id_or_iqama(matched_str)
                if is_valid and self._is_enabled(ent_type, enabled_types):
                    chk_ok = meta.get("is_valid_checksum", False)
                    conf = 0.98 if chk_ok else 0.75
                    span = self._build_span(
                        norm_res, text, m.start(), m.end(),
                        entity_type=ent_type,
                        normalized_val=matched_str,
                        confidence=conf,
                        metadata=meta,
                        is_valid_checksum=chk_ok,
                    )
                    if span:
                        candidates.append(span)

        # -------------------------------------------------------------
        # E. Credit / Debit Cards (13-19 digits, Luhn valid)
        # -------------------------------------------------------------
        if self._is_enabled(EntityType.CREDIT_CARD, enabled_types):
            card_regex = re.compile(r"\b(?:\d[ -]*?){13,19}\b")
            for m in card_regex.finditer(norm_text):
                matched_str = m.group(0)
                is_valid, meta = validate_credit_card(matched_str)
                if is_valid:
                    span = self._build_span(
                        norm_res, text, m.start(), m.end(),
                        entity_type=EntityType.CREDIT_CARD,
                        normalized_val=re.sub(r"[\s-]+", "", matched_str),
                        confidence=0.99,
                        metadata=meta,
                        is_valid_checksum=True,
                    )
                    if span:
                        candidates.append(span)

        # -------------------------------------------------------------
        # F. Phone Numbers (Regional MENA + International)
        # -------------------------------------------------------------
        if self._is_enabled(EntityType.PHONE_NUMBER, enabled_types):
            # Matches strings resembling phone numbers with digits, dashes, spaces, parentheses (strictly single-line)
            phone_candidate_regex = re.compile(r"(?:\+?[\d \t()-]{8,20}\b)")
            for m in phone_candidate_regex.finditer(norm_text):
                full_val = m.group(0)
                l_strip = len(full_val) - len(full_val.lstrip(" \t"))
                r_strip = len(full_val) - len(full_val.rstrip(" \t"))
                matched_str = full_val.strip(" \t")
                is_valid, meta = validate_regional_phone(matched_str)
                if is_valid:
                    actual_start = m.start() + l_strip
                    actual_end = m.end() - r_strip
                    span = self._build_span(
                        norm_res, text, actual_start, actual_end,
                        entity_type=EntityType.PHONE_NUMBER,
                        normalized_val=meta.get("clean_number", matched_str),
                        confidence=0.90,
                        metadata=meta,
                    )
                    if span:
                        candidates.append(span)

        # -------------------------------------------------------------
        # G. Email Addresses
        # -------------------------------------------------------------
        if self._is_enabled(EntityType.EMAIL_ADDRESS, enabled_types):
            for m in EMAIL_REGEX.finditer(norm_text):
                span = self._build_span(
                    norm_res, text, m.start(), m.end(),
                    entity_type=EntityType.EMAIL_ADDRESS,
                    normalized_val=m.group(0).lower(),
                    confidence=0.99,
                )
                if span:
                    candidates.append(span)

        # -------------------------------------------------------------
        # H. IP Addresses (IPv4 and IPv6)
        # -------------------------------------------------------------
        if self._is_enabled(EntityType.IP_ADDRESS, enabled_types):
            for m in IPV4_REGEX.finditer(norm_text):
                span = self._build_span(
                    norm_res, text, m.start(), m.end(),
                    entity_type=EntityType.IP_ADDRESS,
                    normalized_val=m.group(0),
                    confidence=0.95,
                    metadata={"version": "IPv4"},
                )
                if span:
                    candidates.append(span)

            for m in IPV6_REGEX.finditer(norm_text):
                span = self._build_span(
                    norm_res, text, m.start(), m.end(),
                    entity_type=EntityType.IP_ADDRESS,
                    normalized_val=m.group(0),
                    confidence=0.95,
                    metadata={"version": "IPv6"},
                )
                if span:
                    candidates.append(span)

        # 2. Filter by confidence threshold
        filtered = [s for s in candidates if s.confidence >= threshold]

        # 3. Deduplicate overlapping spans
        resolved = self._resolve_overlapping_spans(filtered)
        return resolved

    def _build_span(
        self,
        norm_res: NormalizedText,
        original_text: str,
        norm_start: int,
        norm_end: int,
        entity_type: EntityType,
        normalized_val: str,
        confidence: float,
        metadata: Optional[Dict[str, Any]] = None,
        is_valid_checksum: Optional[bool] = None,
    ) -> Optional[PIISpan]:
        """Constructs and verifies a PIISpan mapped from normalized coordinates to raw text."""
        orig_start, orig_end = norm_res.map_span_to_original(norm_start, norm_end)
        if orig_start >= orig_end or orig_end > len(original_text):
            return None

        raw_substring = original_text[orig_start:orig_end]

        try:
            span = PIISpan(
                entity_type=entity_type,
                raw_text=raw_substring,
                normalized_text=normalized_val,
                start_char=orig_start,
                end_char=orig_end,
                confidence=confidence,
                metadata=metadata or {},
                is_valid_checksum=is_valid_checksum,
            )
            # Guarantee 100% exact source grounding
            if span.verify_grounding(original_text):
                return span
        except ValueError:
            return None

        return None

    @staticmethod
    def _is_enabled(entity_type: EntityType, enabled_types: Optional[Set[EntityType]]) -> bool:
        if enabled_types is None:
            return True
        return entity_type in enabled_types

    @staticmethod
    def _resolve_overlapping_spans(spans: List[PIISpan]) -> List[PIISpan]:
        """Resolves overlapping entity spans based on priority, checksum validity, and span length."""
        if len(spans) <= 1:
            return sorted(spans, key=lambda s: s.start_char)

        # Sort criteria:
        # 1. Checksum validity (True > None > False)
        # 2. Priority of entity type (higher is more specific)
        # 3. Span length (longer match preferred over substring)
        # 4. Confidence
        def sort_key(s: PIISpan) -> Tuple[int, int, int, float]:
            prio = PRIORITY_MAP.get(s.entity_type, 0)
            chk_score = 2 if s.is_valid_checksum is True else (1 if s.is_valid_checksum is None else 0)
            return (prio, chk_score, s.span_length, s.confidence)

        sorted_candidates = sorted(spans, key=sort_key, reverse=True)

        accepted: List[PIISpan] = []
        for candidate in sorted_candidates:
            # Check collision with already accepted spans
            collides = False
            for acc in accepted:
                # Two intervals [a, b) and [c, d) overlap if max(a, c) < min(b, d)
                if max(candidate.start_char, acc.start_char) < min(candidate.end_char, acc.end_char):
                    collides = True
                    break

            if not collides:
                accepted.append(candidate)

        # Return sorted by character position
        return sorted(accepted, key=lambda s: s.start_char)
