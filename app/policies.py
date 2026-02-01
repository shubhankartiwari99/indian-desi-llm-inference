from typing import Optional

MIN_CHARS = 20

GENERIC_FALLBACK = (
    "I'm still learning and may not have a complete answer yet. "
    "Could you try asking in a different way?"
)

EMOTIONAL_FALLBACK = {  
    "en": (
        "I hear you. You're not alone. It's okay to feel this way. "
        "Want to talk a bit more about what's been weighing on you?"
    ),
    "hi": (
        "मैं समझ सकता हूँ। आप अकेले नहीं हैं। "
        "ऐसा महसूस होना ठीक है। अगर चाहें तो थोड़ा और बताइए।"
    ),
}

def apply_response_policies(text: str, intent: Optional[str] = None, lang: str = "en") -> str:
    if not text:
        if intent == "emotional":
            return EMOTIONAL_FALLBACK.get(lang, EMOTIONAL_FALLBACK["en"])
        return GENERIC_FALLBACK

    cleaned = text.strip()

    if cleaned in {"-", ".", "..."}:
        if intent == "emotional":
            return EMOTIONAL_FALLBACK.get(lang, EMOTIONAL_FALLBACK["en"])
        return GENERIC_FALLBACK

    if len(cleaned) < MIN_CHARS:
        if intent == "emotional":
            return EMOTIONAL_FALLBACK.get(lang, EMOTIONAL_FALLBACK["en"])
        return GENERIC_FALLBACK

    return cleaned