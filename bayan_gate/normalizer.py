"""Arabic-Indic numeral normalizer and unicode span mapping engine.

Provides:
- Bidirectional conversion between Western Arabic digits (0-9) and Eastern Arabic-Indic digits (٠-٩, ۰-۹).
- Zero-drift span mapping between normalized text and raw unicode text.
- Arabic diacritic (Tashkeel) and Tatweel (Kashida) normalization with coordinate tracking.
- Reversible index maps ensuring 100% accurate PII redaction without offset corruption.
"""

from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

# Eastern Arabic-Indic digits (Mashriqi: Saudi, Egypt, Levant, Gulf)
EASTERN_ARABIC_INDIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"  # U+0660 to U+0669

# Extended Arabic-Indic digits (Persian, Urdu)
EXTENDED_ARABIC_INDIC_DIGITS = "۰۱۲۳۴۵۶۷۸۹"  # U+06F0 to U+06F9

# Western Arabic digits (ASCII)
WESTERN_ARABIC_DIGITS = "0123456789"

# Lookup translation tables for fast character translation
_TO_WESTERN_TABLE = str.maketrans({
    # Eastern Arabic-Indic -> Western
    0x0660: "0", 0x0661: "1", 0x0662: "2", 0x0663: "3", 0x0664: "4",
    0x0665: "5", 0x0666: "6", 0x0667: "7", 0x0668: "8", 0x0669: "9",
    # Extended Arabic-Indic (Persian/Urdu) -> Western
    0x06F0: "0", 0x06F1: "1", 0x06F2: "2", 0x06F3: "3", 0x06F4: "4",
    0x06F5: "5", 0x06F6: "6", 0x06F7: "7", 0x06F8: "8", 0x06F9: "9",
})

_TO_EASTERN_TABLE = str.maketrans({
    ord("0"): "٠", ord("1"): "١", ord("2"): "٢", ord("3"): "٣", ord("4"): "٤",
    ord("5"): "٥", ord("6"): "٦", ord("7"): "٧", ord("8"): "٨", ord("9"): "٩",
})

# Arabic Tashkeel / Harakat characters
# Fathatan, Dammatan, Kasratan, Fatha, Damma, Kasra, Shadda, Sukun, Dagger Alef, Superscript Alef
TASHKEEL_CODEPOINTS = {
    0x064B,  # Fathatan
    0x064C,  # Dammatan
    0x064D,  # Kasratan
    0x064E,  # Fatha
    0x064F,  # Damma
    0x0650,  # Kasra
    0x0651,  # Shadda
    0x0652,  # Sukun
    0x0653,  # Maddah Above
    0x0654,  # Hamza Above
    0x0655,  # Hamza Below
    0x0670,  # Superscript Alef (Dagger Alef)
}

# Tatweel / Kashida
TATWEEL_CODEPOINT = 0x0640


@dataclass(frozen=True)
class NormalizedText:
    """Represents normalized text with bidirectional character coordinate mapping.

    Attributes:
        original_text: The unmodified input string.
        normalized_text: The normalized string after applying transformations.
        index_map: Maps each index in `normalized_text` to its start index in `original_text`.
        reverse_map: Maps each index in `original_text` to its index in `normalized_text`,
                     or -1 if the character was omitted.
    """
    original_text: str
    normalized_text: str
    index_map: List[int]
    reverse_map: List[int]

    def map_span_to_original(self, norm_start: int, norm_end: int) -> Tuple[int, int]:
        """Maps a character span [norm_start:norm_end] in normalized_text to [orig_start:orig_end] in original_text.

        Args:
            norm_start: Zero-indexed start offset in normalized_text.
            norm_end: Zero-indexed end offset (exclusive) in normalized_text.

        Returns:
            Tuple of (orig_start, orig_end) representing the exact slice in original_text.
        """
        if norm_start < 0:
            norm_start = 0
        if norm_end < norm_start:
            norm_end = norm_start

        norm_len = len(self.normalized_text)
        if norm_len == 0 or len(self.original_text) == 0:
            return 0, 0

        # Boundary clamping
        if norm_start >= norm_len:
            return len(self.original_text), len(self.original_text)
        if norm_end > norm_len:
            norm_end = norm_len

        orig_start = self.index_map[norm_start]

        # For orig_end: include the last character plus any trailing diacritics/kashidas
        if norm_start == norm_end:
            return orig_start, orig_start

        if norm_end < norm_len:
            # Span ends before the next character in normalized text
            orig_end = self.index_map[norm_end]
        else:
            # Span extends to the end of normalized text; capture remaining original trailing characters
            orig_end = len(self.original_text)

        return orig_start, orig_end

    def extract_original_span(self, norm_start: int, norm_end: int) -> str:
        """Extracts the exact raw substring from original_text corresponding to a normalized span."""
        orig_start, orig_end = self.map_span_to_original(norm_start, norm_end)
        return self.original_text[orig_start:orig_end]


class ArabicIndicNormalizer:
    """High-performance unicode normalization engine for Arabic and MENA regional text."""

    @staticmethod
    def to_western_digits(text: str) -> str:
        """Converts Eastern Arabic-Indic (٠-٩) and Persian (۰-۹) digits to Western ASCII digits (0-9).

        1:1 character translation preserving identical string length and character offsets.
        """
        if not text:
            return ""
        return text.translate(_TO_WESTERN_TABLE)

    @staticmethod
    def to_arabic_indic_digits(text: str) -> str:
        """Converts Western ASCII digits (0-9) to Eastern Arabic-Indic digits (٠-٩).

        1:1 character translation preserving identical string length and character offsets.
        """
        if not text:
            return ""
        return text.translate(_TO_EASTERN_TABLE)

    @staticmethod
    def has_arabic_indic_digits(text: str) -> bool:
        """Returns True if the text contains any Eastern Arabic-Indic or Persian digits."""
        if not text:
            return False
        return any(
            (0x0660 <= ord(c) <= 0x0669) or (0x06F0 <= ord(c) <= 0x06F9)
            for c in text
        )

    @staticmethod
    def has_arabic_text(text: str) -> bool:
        """Returns True if the text contains any Arabic unicode characters."""
        if not text:
            return False
        return any(
            (0x0600 <= ord(c) <= 0x06FF) or  # Arabic
            (0x0750 <= ord(c) <= 0x077F) or  # Arabic Supplement
            (0x08A0 <= ord(c) <= 0x08FF) or  # Arabic Extended-A
            (0xFB50 <= ord(c) <= 0xFDFF) or  # Arabic Presentation Forms-A
            (0xFE70 <= ord(c) <= 0xFEFF)      # Arabic Presentation Forms-B
            for c in text
        )

    @classmethod
    def normalize_text(
        cls,
        text: str,
        strip_tashkeel: bool = True,
        strip_tatweel: bool = True,
        convert_digits: bool = True,
        normalize_alef: bool = False,
        normalize_teh_marbuta: bool = False,
        normalize_yeh: bool = False,
        normalize_kaf: bool = False,
    ) -> NormalizedText:
        """Normalizes Arabic text with full character-level coordinate tracking.

        Args:
            text: Raw input string.
            strip_tashkeel: Remove Arabic diacritical marks (Fatha, Damma, Kasra, Shadda, etc.).
            strip_tatweel: Remove Tatweel/Kashida (ـ) typographic elongation characters.
            convert_digits: Convert Eastern Arabic-Indic digits to Western ASCII digits.
            normalize_alef: Normalize forms of Alef (أ, إ, آ, ٱ) to bare Alef (ا).
            normalize_teh_marbuta: Normalize Teh Marbuta (ة) to Heh (ه).

        Returns:
            NormalizedText containing the transformed string and reversible index maps.
        """
        if not text:
            return NormalizedText(
                original_text="",
                normalized_text="",
                index_map=[],
                reverse_map=[],
            )

        norm_chars: List[str] = []
        index_map: List[int] = []
        reverse_map: List[int] = [-1] * len(text)

        norm_idx = 0
        for orig_idx, ch in enumerate(text):
            cp = ord(ch)

            # 1. Check for omitted characters
            if strip_tashkeel and cp in TASHKEEL_CODEPOINTS:
                continue

            if strip_tatweel and cp == TATWEEL_CODEPOINT:
                continue

            # 2. Check for character transformations
            target_ch = ch

            if convert_digits:
                if (0x0660 <= cp <= 0x0669) or (0x06F0 <= cp <= 0x06F9):
                    target_ch = _TO_WESTERN_TABLE.get(cp, ch)

            if normalize_alef:
                # Alef with Hamza Above (أ), Alef with Hamza Below (إ), Alef with Madda (آ), Alef Wasla (ٱ)
                if cp in (0x0622, 0x0623, 0x0625, 0x0671):
                    target_ch = "ا"

            if normalize_teh_marbuta:
                # Teh Marbuta (ة) -> Heh (ه)
                if cp == 0x0629:
                    target_ch = "ه"

            if normalize_yeh:
                # Persian Yeh (ی, U+06CC), Arabic Alef Maksura (ى, U+0649) -> Arabic Yeh (ي, U+064A)
                if cp in (0x06CC, 0x0649):
                    target_ch = "ي"

            if normalize_kaf:
                # Persian/Urdu Keheh (ک, U+06A9) -> Arabic Kaf (ك, U+0643)
                if cp == 0x06A9:
                    target_ch = "ك"

            norm_chars.append(target_ch)
            index_map.append(orig_idx)
            reverse_map[orig_idx] = norm_idx
            norm_idx += 1

        normalized_str = "".join(norm_chars)
        return NormalizedText(
            original_text=text,
            normalized_text=normalized_str,
            index_map=index_map,
            reverse_map=reverse_map,
        )
