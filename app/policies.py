from typing import Optional
from collections import Counter
import re

MIN_CHARS = 20
MAX_CHARS = 280

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

EXPLANATORY_FALLBACK = {
    "en": (
        "Here is a simple explanation: start with a short definition, then one small example. "
        "Tell me what part is confusing and I will tailor it."
    ),
    "hi": (
        "Simple shabdon mein: pehle chhoti definition, phir ek chhota example. "
        "Aap batao kis part mein confusion hai, main usi hisaab se samjha dunga."
    ),
}

FACTUAL_FALLBACK = {
    "en": "I do not have that fact with confidence right now.",
    "hi": "Mujhe is fact ka pakka jawab abhi nahi pata.",
}

CONVERSATIONAL_FALLBACK = {
    "en": "I hear you. Tell me what you need help with, and I will do my best.",
    "hi": "Main samajh raha hoon. Aap batao kis cheez mein help chahiye, main poori koshish karunga.",
}

REFUSAL_FALLBACK = (
    "I can't help with harmful or illegal actions. "
    "I can help with safe and legal alternatives."
)

UNCERTAIN_FALLBACK = (
    "I can't predict that with certainty. "
    "I can help you think through likely scenarios and risk-aware next steps."
)

TOKEN_RE = re.compile(r"\w+", re.UNICODE)

_STOPWORDS = {
    # English
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "but",
    "by",
    "did",
    "do",
    "does",
    "for",
    "from",
    "had",
    "has",
    "have",
    "how",
    "i",
    "in",
    "is",
    "it",
    "its",
    "of",
    "on",
    "or",
    "please",
    "tell",
    "that",
    "the",
    "their",
    "this",
    "to",
    "was",
    "were",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "with",
    "you",
    "your",
    # Common romanized Hindi/Hinglish fillers
    "aur",
    "hai",
    "hota",
    "hoti",
    "ho",
    "kya",
    "ka",
    "ke",
    "ki",
    "ko",
    "mein",
    "me",
    "se",
    "par",
    "kyu",
    "kyon",
    "kaise",
    "kab",
    "kaun",
}

EMPATHY_MARKERS = (
    "i hear you",
    "that sounds",
    "understandable",
    "you are not alone",
    "your feelings are valid",
    "i am here with you",
    "it's okay to feel",
)

UNCERTAINTY_MARKERS = (
    "cannot",
    "can't",
    "not possible",
    "uncertain",
    "no one can",
    "cannot guarantee",
    "can't guarantee",
    "cannot predict",
    "can't predict",
    "do not know for sure",
    "don't know for sure",
)

HARMFUL_PROMPT_MARKERS = (
    "hack",
    "phishing",
    "bomb",
    "explosive",
    "poison",
    "clone login",
    "collect passwords",
    "sabotage",
    "trick bank users",
    "fake document",
    "fake bank statement",
    "forged",
    "fraud",
    "hurt myself",
    "self-harm",
    "suicide",
    "suicidal",
    "kill myself",
    "end my life",
    "hurt someone",
    "kill",
    "malware",
    "ransomware",
    "blackmail",
    "spyware",
    "deepfake",
    "without consent",
    "forge medical",
    "forgery",
    "insurance claim",
    "fake report",
    "medical report",
    "steal corporate",
    "aadhaar",
    "aadhar",
    "pan card",
    "passport",
    "id proof",
    "fake proof",
    "edit pdf",
    "pdf edit",
    "salary slip",
    "salary slips",
    "payslip",
    "pay slip",
    "believable fake",
    "jugaad",
    "arrange proof",
    "impersonate",
    "impersonation",
    "2fa",
    "bypass 2fa",
    "steal otp",
    "steal password",
    "illegal",
    "फिशिंग",
    "हैक",
    "बम",
    "ज़हर",
    "जहर",
    "फर्जी",
    "आत्महत्या",
)

SOCIAL_ENGINEERING_PATTERNS = [
    # Drafting messages to coax verification codes ("6-digit code") is classic phishing even without "OTP".
    re.compile(
        r"(?=.*\b(verification|security|login|auth|authentication|one[- ]?time|2fa)\b.*\b(code|passcode|otp)\b)"
        r"(?=.*\b(draft|template|message|sms|text|email|whatsapp)\b)"
        r"(?=.*\b(share|sharing|shared|forward|forwarding|provide|providing|provided|tell|telling|give|giving|reply|replying)\b)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?=.*\b6\s*[- ]?\s*digit\b)(?=.*\b(code|passcode|otp)\b)"
        r"(?=.*\b(draft|template|message|sms|text|email|whatsapp)\b)"
        r"(?=.*\b(share|sharing|shared|forward|forwarding|provide|providing|provided|tell|telling|give|giving|reply|replying)\b)",
        re.IGNORECASE,
    ),
]

DOC_FRAUD_PATTERNS = [
    # High-confidence doc fraud intent: editing/cleaning a PDF/agreement for submission/approval.
    re.compile(
        r"(?=.*\b(pdf|document|agreement|statement|proof|payslip|salary slip)\b)"
        r"(?=.*\b(edit|edited|modify|modified|alter|adjust|clean|photoshop)\b)"
        r"(?=.*\b(submit|submission|approval|loan|kyc|verification|visa|claim)\b)",
        re.IGNORECASE,
    ),
]


def _script_bucket(ch: str):
    code = ord(ch)
    if ("a" <= ch.lower() <= "z"):
        return "latin"
    if 0x0900 <= code <= 0x097F:
        return "devanagari"
    if 0x0400 <= code <= 0x04FF:
        return "cyrillic"
    if 0x0370 <= code <= 0x03FF:
        return "greek"
    if 0x0600 <= code <= 0x06FF:
        return "arabic"
    if 0x4E00 <= code <= 0x9FFF:
        return "cjk"
    if 0x3040 <= code <= 0x30FF:
        return "jp_kana"
    if 0xAC00 <= code <= 0xD7AF:
        return "hangul"
    return None


def _looks_gibberish(text: str) -> bool:
    if len(text) > MAX_CHARS:
        return True

    tokens = TOKEN_RE.findall(text)
    if len(tokens) <= 2 and len(text) > 80:
        return True

    meaningful = [t.lower() for t in tokens if len(t) >= 4]
    if len(meaningful) >= 6:
        common_count = Counter(meaningful).most_common(1)[0][1]
        if common_count / len(meaningful) >= 0.30:
            return True

    script_counts = Counter()
    letters = 0
    for ch in text:
        if ch.isalpha():
            letters += 1
            bucket = _script_bucket(ch)
            if bucket:
                script_counts[bucket] += 1

    if letters >= 40:
        active_scripts = [
            k for k, v in script_counts.items() if (v / letters) >= 0.10
        ]
        if len(active_scripts) >= 3:
            return True

    return False


def _fallback_for_intent(intent: Optional[str], lang: str):
    if intent == "emotional":
        return EMOTIONAL_FALLBACK.get(lang, EMOTIONAL_FALLBACK["en"])
    if intent == "conversational":
        return CONVERSATIONAL_FALLBACK.get(lang, CONVERSATIONAL_FALLBACK["en"])
    if intent == "explanatory":
        return EXPLANATORY_FALLBACK.get(lang, EXPLANATORY_FALLBACK["en"])
    if intent == "factual":
        return FACTUAL_FALLBACK.get(lang, FACTUAL_FALLBACK["en"])
    if intent == "uncertain":
        return UNCERTAIN_FALLBACK
    if intent == "refusal":
        return REFUSAL_FALLBACK
    return GENERIC_FALLBACK


def _min_chars_for_intent(intent: Optional[str]) -> int:
    if intent == "factual":
        return 8
    if intent == "uncertain":
        return 16
    return MIN_CHARS


def _tokens(text: str):
    return [t.lower() for t in TOKEN_RE.findall(text)]

def _content_tokens(text: str):
    return [t for t in _tokens(text) if t not in _STOPWORDS]


def _looks_like_prompt_echo(response: str, prompt: Optional[str]) -> bool:
    if not prompt:
        return False

    response_tokens = _tokens(response)
    prompt_tokens = set(_tokens(prompt))

    if len(response_tokens) < 3:
        return False

    overlap = sum(1 for t in response_tokens if t in prompt_tokens)
    overlap_ratio = overlap / max(1, len(response_tokens))
    return overlap_ratio >= 0.85


def _looks_like_prompt_echo_content(response: str, prompt: Optional[str]) -> bool:
    """
    Softer echo detector for factual/explanatory intents.
    Uses content words (drops stopwords) so direct answers like:
      Q: "Which planet is closest to the Sun?"
      A: "Mercury is the closest planet to the Sun."
    are not misclassified as echo, while pure parroting is still blocked.
    """
    if not prompt:
        return False

    response_tokens = _content_tokens(response)
    prompt_tokens = set(_content_tokens(prompt))

    if len(response_tokens) < 2:
        return False

    overlap = sum(1 for t in response_tokens if t in prompt_tokens)
    overlap_ratio = overlap / max(1, len(response_tokens))

    # If there's at least one new content token, it's an answer, not echo.
    has_new_content = any(t not in prompt_tokens for t in response_tokens)
    return overlap_ratio >= 0.85 and (not has_new_content)


def _fails_intent_quality(cleaned: str, intent: Optional[str], prompt: Optional[str]) -> bool:
    lower = cleaned.lower()

    if intent == "emotional":
        if _looks_like_prompt_echo(cleaned, prompt):
            return True
        return not any(marker in lower for marker in EMPATHY_MARKERS)

    if intent == "conversational":
        # Avoid parroting the user's text back.
        return _looks_like_prompt_echo(cleaned, prompt)

    if intent == "factual":
        return _looks_like_prompt_echo_content(cleaned, prompt)

    if intent == "explanatory":
        if _looks_like_prompt_echo_content(cleaned, prompt):
            return True
        return len(_tokens(cleaned)) < 10

    if intent == "uncertain":
        return not any(marker in lower for marker in UNCERTAINTY_MARKERS)

    return False


def _prompt_indicates_harm(prompt: Optional[str]) -> bool:
    if not prompt:
        return False
    lower = prompt.lower()
    if any(marker in lower for marker in HARMFUL_PROMPT_MARKERS):
        return True
    if any(p.search(lower) for p in SOCIAL_ENGINEERING_PATTERNS):
        return True
    return any(p.search(lower) for p in DOC_FRAUD_PATTERNS)


def apply_response_policies(
    text: str,
    intent: Optional[str] = None,
    lang: str = "en",
    prompt: Optional[str] = None,
) -> str:
    # Hard safety rail: refusal responses are always sanitized to safe fallback.
    if intent == "refusal" or _prompt_indicates_harm(prompt):
        return REFUSAL_FALLBACK

    if not text:
        return _fallback_for_intent(intent, lang)

    cleaned = text.strip()

    if cleaned in {"-", ".", "..."}:
        return _fallback_for_intent(intent, lang)

    if len(cleaned) < _min_chars_for_intent(intent):
        return _fallback_for_intent(intent, lang)

    if _looks_gibberish(cleaned):
        return _fallback_for_intent(intent, lang)

    if _fails_intent_quality(cleaned, intent, prompt):
        return _fallback_for_intent(intent, lang)

    return cleaned
