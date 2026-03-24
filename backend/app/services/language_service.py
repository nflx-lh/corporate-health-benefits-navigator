"""Language detection service for multilingual query support (B-1701).

Detects the language of an employee query using langdetect.
Falls back gracefully if the library is unavailable.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# Supported language codes → display names
SUPPORTED_LANGUAGES: dict[str, str] = {
    "en": "English",
    "zh-cn": "Mandarin (Simplified)",
    "zh-tw": "Mandarin (Traditional)",
    "zh": "Mandarin",
    "ms": "Malay",
    "ta": "Tamil",
    "vi": "Vietnamese",
    "ja": "Japanese",
    "ko": "Korean",
}

# Regex patterns for non-Latin scripts — unambiguous language signals
_CJK_PATTERN = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")          # Chinese characters
_HIRAGANA_KATAKANA = re.compile(r"[\u3040-\u30ff]")                  # Japanese kana
_HANGUL = re.compile(r"[\uac00-\ud7af\u1100-\u11ff]")                # Korean hangul
_TAMIL_SCRIPT = re.compile(r"[\u0b80-\u0bff]")                       # Tamil script
_DEVANAGARI = re.compile(r"[\u0900-\u097f]")                         # Hindi/Sanskrit

# Try importing langdetect — optional dependency
_LANGDETECT_AVAILABLE = False
try:
    import langdetect
    from langdetect import DetectorFactory
    DetectorFactory.seed = 0  # reproducible detection results
    _LANGDETECT_AVAILABLE = True
except ImportError:
    pass


def _detect_by_script(text: str) -> str | None:
    """Fast script-based detection for unambiguous non-Latin scripts."""
    if _HIRAGANA_KATAKANA.search(text):
        return "ja"
    if _HANGUL.search(text):
        return "ko"
    if _TAMIL_SCRIPT.search(text):
        return "ta"
    # CJK characters alone — could be Chinese or Japanese mixed; default Chinese
    if _CJK_PATTERN.search(text) and not _HIRAGANA_KATAKANA.search(text):
        return "zh-cn"
    return None


def detect_language(text: str) -> tuple[str, float]:
    """Detect the language of text.

    Returns:
        (lang_code, confidence) — lang_code is a BCP-47-style code (e.g. "en", "ja").
        Falls back to ("en", 0.0) on failure.
    """
    if not text or not text.strip():
        return "en", 0.0

    # Script-based fast path — highly reliable for CJK/Hangul/Tamil
    script_lang = _detect_by_script(text)
    if script_lang:
        return script_lang, 1.0

    if not _LANGDETECT_AVAILABLE:
        return "en", 0.0

    try:
        results = langdetect.detect_langs(text)
        if results:
            top = results[0]
            lang = top.lang
            # Normalize zh variants
            if lang.startswith("zh"):
                lang = "zh-cn"
            return lang, round(top.prob, 3)
    except Exception as exc:
        logger.debug("langdetect failed: %s", exc)

    return "en", 0.0


def is_english(lang_code: str) -> bool:
    """Return True if the language code represents English."""
    return lang_code.startswith("en")


def language_display_name(lang_code: str) -> str:
    """Return a human-readable display name for the language code."""
    return SUPPORTED_LANGUAGES.get(lang_code, lang_code.upper())
