import re


UNCERTAIN_PATTERNS = [
    re.compile(r"\bcan you\b.*\b(guarantee|predict|promise|assure)\b"),
    re.compile(r"\b(who|which)\s+will\s+definitely\b"),
    re.compile(r"\bwho\s+will\s+surely\b"),
    re.compile(r"\b(after the next|next)\b.*\b(election|polls?)\b"),
    re.compile(r"\bpredict\b.*\bexact\b"),
    re.compile(r"\bexact\b.*\b(stock|market|winner|result|price|top)\b"),
    re.compile(r"\b(100%|100 percent|sure[- ]?shot|pakka)\b"),
    re.compile(r"\b(will|can)\b.*\b(peak|approve|profitable)\b"),
    re.compile(r"\b(impossible|nameumkin|namumkin)\b"),
    re.compile(r"\bexact\s+(date|day|time)\b.*\b(this year|next year|next month|next week|this month)\b"),
    re.compile(r"\b(inr\s*/\s*usd|usd\s*/\s*inr|exchange rate|forex|fx)\b.*\b(highest|peak|top|exact)\b"),
    re.compile(r"\b(highest|peak|top)\b.*\b(this year|next year|next month|next week)\b"),
    # Directional prediction pressure (domain-agnostic): "next month ... up or down" / "no it depends".
    re.compile(
        r"\b(next\s+(week|month|year)|this\s+(week|month|year)|tomorrow)\b.*\b(up\s+or\s+down|rise\s+or\s+fall|increase\s+or\s+decrease|go\s+up|go\s+down)\b"
    ),
    re.compile(
        r"\b(up\s+or\s+down|rise\s+or\s+fall|increase\s+or\s+decrease|go\s+up|go\s+down)\b.*\b(next\s+(week|month|year)|this\s+(week|month|year)|tomorrow)\b"
    ),
    re.compile(r"\bno\b.*\bit\s+depends\b"),
]

TERM_MEANING_PATTERN = re.compile(r"\bwhat\s+does\b.*\bmean\b", re.IGNORECASE)

EMOTIONAL_TIME_PATTERNS = [
    re.compile(r"\b(\d{1,2})\s*[- ]?\s*(min|mins|minute|minutes)\b"),
    re.compile(r"\btonight\b"),
    re.compile(r"\bthis\s+evening\b"),
    re.compile(r"\bright\s+now\b"),
    re.compile(r"\btoday\b"),
    re.compile(r"\baaj\b"),
    re.compile(r"\babhi\b"),
]

EMOTIONAL_CONTEXT_MARKERS = [
    "exam",
    "interview",
    "pressure",
    "family pressure",
    "career pressure",
    "guilt",
    "tension",
    "overthinking",
    "procrastinat",
    "burnout",
    "exhausted",
    "snappy",
    "irritated",
    "mind noisy",
    "noisy mind",
    "mind racing",
    "dimag",
    "mann",
]

EMOTIONAL_ACTION_MARKERS = [
    "reset",
    "cope",
    "deal with",
    "deal",
    "handle",
    "manage",
    "get through",
    "get over",
    "calm down",
    "calm",
    "ground",
    "focus",
    "practical step",
    "small step",
    "kya karun",
    "what should i do",
]

FACTUAL_PATTERNS = [
    re.compile(r"(?:^|[\s:,.!?])\s*(who|what|which|where|when)\b"),
    re.compile(r"(किसने|कौन|कब|क्या)"),
    re.compile(r"\b(kis saal|which year)\b"),
]

REFUSAL_PATTERNS = [
    re.compile(
        r"\b(for education only|just curious|hypothetically|step[- ]?by[- ]?step|detailed instructions|fastest method)\b.*\b(hack|phishing|bomb|poison|fake|fraud|forg|hurt|kill|malware|ransomware)\b"
    ),
    re.compile(
        r"\b(hack|phishing|bomb|poison|fake|fraud|forge|forged|steal|hurt|kill|malware|ransomware|blackmail)\b.*\b(account|instagram|email|bank|loan|documents?|statement|password|otp|sms|login|template)\b"
    ),
    re.compile(
        r"\b(spyware|deepfake|forge|forgery|fake)\b.*\b(phone|consent|report|medical|insurance|claim)\b"
    ),
    re.compile(
        r"\b(aadhaar|aadhar|pan|passport|id proof|proof)\b.*\b(edit|edited|modify|modified|fake|forg|generate|create|arrange)\b"
    ),
    re.compile(
        r"\b(salary slip|salary slips|pay slip|payslip)\b.*\b(fake|forg|believable|loan|approval)\b"
    ),
    re.compile(
        r"\b(clone|sabotage|disable|bypass|explosive|detonate|trick)\b.*\b(login|password|otp|bank|laptop|device|account|users)\b"
    ),
    re.compile(r"\b(make|create|give|provide)\b.*\b(fake bank statement|fake documents?|phishing sms|bomb)\b"),
    re.compile(r"\b(self[- ]?harm|hurt myself|suicide|suicidal|kill\\s+myself|end\\s+my\\s+life)\b"),
    re.compile(r"(फिशिंग|हैक|बम|ज़हर|जहर|फर्जी|धोखा|घोटाला|नुकसान पहुँचाऊँ)"),
    # Social-engineering / scam euphemisms (verification code / 6-digit code) without explicit "OTP".
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
    # Document fraud euphemisms: "edit/adjust/clean" a PDF/agreement for submission/approval.
    re.compile(
        r"(?=.*\b(pdf|document|agreement|statement|proof|payslip|salary slip)\b)"
        r"(?=.*\b(edit|edited|modify|modified|alter|adjust|clean|photoshop)\b)"
        r"(?=.*\b(submit|submission|approval|loan|kyc|verification|visa|claim)\b)",
        re.IGNORECASE,
    ),
]


def _contains_any(text: str, needles):
    return any(needle in text for needle in needles)


def _matches_any_pattern(text: str, patterns):
    return any(pattern.search(text) for pattern in patterns)

def _is_emotional_override(prompt_lower: str) -> bool:
    has_time = any(p.search(prompt_lower) for p in EMOTIONAL_TIME_PATTERNS)
    has_context = any(marker in prompt_lower for marker in EMOTIONAL_CONTEXT_MARKERS)
    has_action = any(marker in prompt_lower for marker in EMOTIONAL_ACTION_MARKERS)

    # The user is asking how to function/cope (emotional), even if they say "batao".
    return has_action and (has_context or has_time)


def detect_intent(prompt: str) -> str:
    """
    Lightweight heuristic-based intent detection.
    Returns one of:
    - factual
    - explanatory
    - conversational
    - emotional
    - uncertain
    - refusal
    """

    p = prompt.lower().strip()

    refusal_triggers = [
        "hack",
        "hacking",
        "instagram",
        "phishing",
        "phish",
        "bomb",
        "explosive",
        "clone login",
        "sabotage",
        "trick bank users",
        "collect passwords",
        "hurt myself",
        "self-harm",
        "suicide",
        "suicidal",
        "kill myself",
        "end my life",
        "hurt someone",
        "kill",
        "poison",
        "fake bank statement",
        "fake documents",
        "forged documents",
        "fraud",
        "steal",
        "illegal",
        "scam",
        "blackmail",
        "ransomware",
        "malware",
        "spyware",
        "deepfake",
        "without consent",
        "forge medical",
        "forgery",
        "insurance claim",
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
        "otp",
        "account password",
        "weapon",
    ]

    emotional_triggers = [
        "i feel",
        "feel lost",
        "feeling",
        "stress",
        "panic",
        "sleep",
        "insomnia",
        "nind",
        "doom-scrolling",
        "blank feel",
        "toot raha",
        "sad",
        "lonely",
        "anxious",
        "tired",
        "breakup",
        "depressed",
        "overwhelmed",
        "emotionally drained",
        "drained",
        "switch off",
        "can't switch off",
        "falling behind",
        "comparison chal",
        "numb",
        "disconnected",
        "chest heavy",
        "raat ko",
        "panic aa raha",
        "anxious loop",
        "dimag mein",
        "sorted",
        "crumble",
        "crumbling",
        "bhaari",
        "himmat",
        "disappoint",
        "expectations",
        "gharwale",
        "shutting down",
        "shutdown",
        "pretending",
    ]

    uncertain_triggers = [
        "guarantee",
        "for sure",
        "certainty",
        "promise",
        "100%",
        "sure-shot",
        "sure shot",
        "pakka",
        "straight bolo",
        "abhi bata do",
        "definitely",
        "predict exactly",
        "predict the exact",
        "exact price",
        "exact date",
        "exact day",
        "will peak",
        "exact stock market",
        "exchange rate",
        "forex",
        "zero risk",
        "surely succeed",
        "surely",
        "impossible",
        "पक्का",
        "गारंटी",
        "भविष्यवाणी",
        "नामुमकिन",
        "असंभव",
    ]

    explanatory_triggers = [
        "explain",
        "samjhao",
        "samjha",
        "matlab",
        "मतलब",
        "समझाओ",
        "समझाइए",
        "समझा",
        "फर्क",
        "अंतर",
        "कैसे",
        "क्यों",
        "क्यूँ",
        "उदाहरण",
        "आसान",
        "सरल",
        "batao",
        "bataiye",
        "meaning",
        "simple banao",
        "easy banao",
        "beginner level",
        "beginner ko",
        "vs",
        "kaise",
        "kyon",
        "kyu",
        "why",
        "how",
        "fark",
        "analogy",
        "beginner",
        "simple words",
        "meaning",
        "difference between",
    ]

    factual_triggers = [
        "who is",
        "what is",
        "what does",
        "when did",
        "capital of",
        "capital",
        "currency",
        "kab",
        "kitne",
        "kis saal",
        "kaun tha",
        "कब",
        "कितने",
        "किस साल",
        "prime minister",
        "full form",
        "stand for",
        "stands for",
        "प्रधानमंत्री",
        "राजधानी",
        "कौन है",
        "क्या है",
    ]

    if _contains_any(p, refusal_triggers) or _matches_any_pattern(p, REFUSAL_PATTERNS):
        return "refusal"

    if _contains_any(p, uncertain_triggers):
        return "uncertain"
    for pattern in UNCERTAIN_PATTERNS:
        if pattern.search(p):
            return "uncertain"

    # Disambiguate term-definition questions that include words like "stress".
    # Example: "What does 'stress test' mean in engineering?" should be explanatory, not emotional.
    if TERM_MEANING_PATTERN.search(p):
        first_person_markers = (
            "i feel",
            "i am",
            "i'm",
            "im ",
            "my ",
            "for me",
            "mujhe",
            "main ",
            "mera ",
            "meri ",
            "मैं",
            "मुझे",
            "मेरा",
            "मेरी",
        )
        if not any(marker in p for marker in first_person_markers):
            return "explanatory"

    if (_contains_any(p, emotional_triggers) or _is_emotional_override(p)) and not (
        _contains_any(p, uncertain_triggers) or _matches_any_pattern(p, UNCERTAIN_PATTERNS)
    ):
        return "emotional"

    if _contains_any(p, explanatory_triggers):
        return "explanatory"

    if _contains_any(p, factual_triggers):
        return "factual"
    for pattern in FACTUAL_PATTERNS:
        if pattern.search(p):
            return "factual"

    return "conversational"
