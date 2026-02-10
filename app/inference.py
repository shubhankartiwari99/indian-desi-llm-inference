import torch
import re
import threading
from typing import Optional
from app.model_loader import ModelLoader
from app.intent import detect_intent
from app.language import detect_language
from app.policies import apply_response_policies, GENERIC_FALLBACK, REFUSAL_FALLBACK
from app.utils import normalize_output
from app.alignment_memory import AlignmentMemory
from app.voice.state import SessionVoiceState
from app.voice.rotation_memory import RotationMemory


class InferenceEngine:
    TASK_PREFIXES = ("empathy:", "fact:", "explain:", "uncertain:", "refusal:")
    PREFIX_RE = re.compile(r"^\s*(empathy|fact|explain|uncertain|refusal)\s*:\s*(.*)$", re.IGNORECASE)

    # Topic-consistency gate for semantic retrieval (primarily for explanatory intent).
    # This is intentionally lightweight: it aims to drop obviously-wrong memory hits
    # (e.g., \"credit score\" -> \"blockchain\") without doing heavy NLP.
    TOPIC_PUNCT_RE = re.compile(
        r"""[!"#$%&'()*+,\-./:;<=>?@[\\\]^_`{|}~“”‘’…।॥]+""",
        re.UNICODE,
    )
    TOPIC_STOPWORDS = {
        # English glue
        "the",
        "a",
        "an",
        "is",
        "are",
        "to",
        "of",
        "in",
        "on",
        "for",
        "and",
        "or",
        "with",
        "what",
        "who",
        "when",
        "where",
        "why",
        "how",
        "please",
        "kindly",
        "explain",
        "tell",
        "me",
        "my",
        "your",
        "one",
        "line",
        "short",
        "quick",
        "quickly",
        "simple",
        "simply",
        "terms",
        "words",
        "meaning",
        "means",
        "definition",
        "example",
        "examples",
        "keep",
        "beginner",
        "style",
        "level",
        "high",
        "jargon",
        "no",
        "max",
        "lines",
        # Hinglish glue
        "ka",
        "ki",
        "ke",
        "ko",
        "mein",
        "me",
        "par",
        "pe",
        "se",
        "aur",
        "kya",
        "kyu",
        "kyon",
        "kaise",
        "matlab",
        "samjhao",
        "samjha",
        "samjhaao",
        "batao",
        "bata",
        "bataiye",
        "fark",
        "difference",
        # Devanagari glue
        "का",
        "की",
        "के",
        "को",
        "में",
        "पर",
        "से",
        "और",
        "क्या",
        "क्यों",
        "कैसे",
        "मतलब",
        "समझाइए",
        "समझाओ",
        "बताइए",
        "बताओ",
        "फर्क",
        "एक",
        "लाइन",
        "आसान",
        "सरल",
        "शब्दों",
    }

    TOPIC_CANON = {
        # Common plural / variants
        "payments": "payment",
        "scores": "score",
        "servers": "server",
        "keys": "key",
        "tests": "test",
        "testing": "test",
        # Hinglish/Hindi normalization for key domains
        "udhaar": "credit",
        "उधार": "credit",
        "cibil": "credit",
        "mehngai": "inflation",
        "महंगाई": "inflation",
        "मुद्रास्फीति": "inflation",
        "encrypt": "encryption",
        "encrypted": "encryption",
        "encrypting": "encryption",
        "caching": "cache",
        "cached": "cache",
        "db": "database",
        "tls": "https",
        "ssl": "https",
        "यूपीआई": "upi",
    }

    TOPIC_CRITICAL = {
        # Single-token topics
        "burnout",
        "inflation",
        "encryption",
        "upi",
        "blockchain",
        "http",
        "https",
        # Phrase topics (we add these when component tokens are present)
        "credit_score",
        "stress_test",
        "cloud_computing",
        "vector_database",
    }

    @classmethod
    def _extract_topic_tokens(cls, text: str) -> set:
        if not text:
            return set()

        toks = set()
        simplified = cls.TOPIC_PUNCT_RE.sub(" ", text.lower())
        for raw in simplified.split():
            if raw in cls.TOPIC_STOPWORDS:
                continue
            canon = cls.TOPIC_CANON.get(raw, raw)
            if canon in cls.TOPIC_STOPWORDS:
                continue
            toks.add(canon)

        # Phrase-level markers to reduce false positives from single words.
        if ("credit" in toks or "cibil" in toks) and "score" in toks:
            toks.add("credit_score")
        if "stress" in toks and "test" in toks:
            toks.add("stress_test")
        if "cloud" in toks and "computing" in toks:
            toks.add("cloud_computing")
        if "vector" in toks and "database" in toks:
            toks.add("vector_database")

        return toks

    @classmethod
    def _is_retrieval_topic_safe(cls, prompt: str, retrieved_text: str) -> bool:
        p_tokens = cls._extract_topic_tokens(prompt)
        r_tokens = cls._extract_topic_tokens(retrieved_text)
        if not p_tokens or not r_tokens:
            return False

        overlap = p_tokens & r_tokens
        has_critical = any(tok in p_tokens for tok in cls.TOPIC_CRITICAL)
        min_overlap = 1 if has_critical else (2 if len(p_tokens) >= 4 else 1)
        if len(overlap) < min_overlap:
            return False

        # If the user mentions a critical topic word/phrase, retrieved text must mention it too.
        for critical in cls.TOPIC_CRITICAL:
            if critical in p_tokens and critical not in r_tokens:
                return False

        return True

    SHAPE_SENTENCE_SPLIT_RE = re.compile(r"[.!?]|[।॥]", re.UNICODE)
    SENTENCE_BOUNDARY_RE = re.compile(r"(?<=[.!?।॥])\\s+", re.UNICODE)

    DEVANAGARI_RE = re.compile(r"[\\u0900-\\u097F]")
    LATIN_RE = re.compile(r"[A-Za-z]")

    EMO_TIMEBOX_RE = re.compile(r"\\b(\\d{1,2})\\s*[- ]?\\s*(min|mins|minute|minutes)\\b", re.IGNORECASE)
    EMO_TIMEBOX_MARKERS = (
        "tonight",
        "right now",
        "today",
        "this evening",
        "aaj",
        "abhi",
        "aaj raat",
        "raat",
        "abhi ke liye",
    )
    EMO_ACTION_REQUEST_MARKERS = (
        "reset",
        "cope",
        "handle",
        "function",
        "calm down",
        "calm",
        "ground",
        "practical",
        "small step",
        "tiny step",
        "help me calm",
        "help me cope",
        "what should i do",
        "kya karun",
        "batao",
        "bataiye",
    )

    HINGLISH_MARKERS = (
        # NOTE: token-level checks; avoid short ambiguous substrings.
        "yaar",
        "bhai",
        "arre",
        "bas",
        "aaj",
        "abhi",
        "kya",
        "karun",
        "nahi",
        "samajh",
        "dimag",
        "mann",
        "gharwale",
    )
    HINGLISH_PHRASE_MARKERS = (
        "kya karun",
        "samajh nahi",
        "samajh nahi aa",
        "log kya kahenge",
        "sharma ji",
        "sharmaji",
    )

    EMO_PUSHBACK_MARKERS = (
        "don't give generic advice",
        "dont give generic advice",
        "no generic advice",
        "please don't give generic advice",
        "please dont give generic advice",
        "don't give advice",
        "dont give advice",
        "no advice",
        "i don't want advice",
        "i dont want advice",
        "don't want exercises",
        "dont want exercises",
        "no exercises",
        "no exercise",
        "don't give exercises",
        "dont give exercises",
    )
    EMO_MINIMAL_REPLIES = {
        "hmm",
        "hm",
        "idk",
        "i don't know",
        "i dont know",
        "dont know",
        "whatever",
        "ok",
        "okay",
        "k",
        "...",
        ".",
    }

    EMO_ACTION_RESPONSE_MARKERS_EN = (
        "try",
        "take",
        "do this",
        "breathe",
        "breathing",
        "inhale",
        "exhale",
        "pause",
        "set a timer",
        "timer",
        "write",
        "walk",
        "stretch",
        "sip water",
        "drink water",
        "step outside",
        "count",
    )
    EMO_ACTION_RESPONSE_MARKERS_HI = (
        "सांस",
        "साँस",
        "धीरे",
        "गिन",
        "टाइमर",
        "करो",
        "करिए",
        "लिख",
        "टहल",
        "कदम",
        "रुको",
        "पानी",
    )

    EXPL_MAX_LINES_RE = re.compile(r"\\b(\\d)\\s*[-–]\\s*(\\d)\\s*lines\\b", re.IGNORECASE)
    EXPL_LINES_MAX_RE = re.compile(r"\\b(\\d)\\s*lines\\s*max\\b", re.IGNORECASE)
    EXPL_EXAMPLE_MARKERS = ("for example", "example:", "example", "उदाहरण", "जैसे")
    EXPL_ENGLISH_LAST_MARKERS = (
        "last line english",
        "last line in english",
        "english later",
        "english mein",
    )
    EXPL_HINDI_FIRST_MARKERS = (
        "hindi first",
        "pehle hindi",
        "pehle hindi mein",
        "पहले हिंदी",
        "पहले हिन्दी",
        "हिंदी पहले",
        "हिन्दी पहले",
    )
    EXPL_NO_JARGON_MARKERS = ("no jargon", "no gyaan", "no gyan", "without jargon")

    # Persona v1: bounded emotional variety (anti-repetition) via skeletons.
    EMO_FALLBACK_EN = (
        "i hear you. you're not alone. it's okay to feel this way. want to talk a bit more about what's been weighing on you?"
    )
    EMO_FALLBACK_HI = (
        "मैं समझ सकता हूँ। आप अकेले नहीं हैं। ऐसा महसूस होना ठीक है। अगर चाहें तो थोड़ा और बताइए।"
    )
    CONV_FALLBACK_EN = "i hear you. tell me what you need help with, and i will do my best."
    CONV_FALLBACK_HI = "main samajh raha hoon. aap batao kis cheez mein help chahiye, main poori koshish karunga."

    EMO_SKELETONS = ("A", "B", "C", "D")

    # B3.2 Emotional Escalation Rule markers and themes
    # Resignation/futility markers that signal disengagement or stuckness
    EMO_RESIGNATION_MARKERS = (
        "nothing has changed",
        "nothing changed",
        "no change",
        "same feeling",
        "same emotions",
        "same thing",
        "same problem",
        "pointless",
        "what's the use",
        "whats the use",
        "this is just how it is",
        "even talking doesn't help",
        "talking doesn't help",
        "i don't know what i'm expecting",
        "dont know what im expecting",
        "kya fayda",
        "same hi rah gaya",
        "kuch nahi badla",
        "ye hi to haal hai",
        "baat karne se kya fayda",
        "na jane kya umeed",
        "बदलाव नहीं आया",
        "कुछ नहीं बदला",
        "एक जैसा है",
        "इसमें कोई मतलब नहीं",
        "बात करने से क्या फायदा",
        "नहीं जानता क्या उम्मीद करूँ",
    )

    # Emotional theme clusters for escalation continuity detection
    EMO_THEME_LOST = (
        "lost",
        "direction",
        "path",
        "clarity",
        "confused",
        "confused about",
        "not sure what",
        "unsure",
        "khud ko samajh time",
        "raah nahi mil",
        "path nahi samajh",
        "kya hona hai",
        "भटका हुआ",
        "दिशा नहीं",
        "समझ नहीं आ रहा",
        "उलझन",
    )
    EMO_THEME_ANXIOUS = (
        "anxious",
        "worried",
        "tense",
        "panic",
        "fear",
        "scared",
        "nervous",
        "what if",
        "flab",
        "pareshaan",
        "chakkar",
        "घबराहट",
        "डर",
        "चिंता",
    )
    EMO_THEME_DRAINED = (
        "drained",
        "exhausted",
        "tired",
        "burnt",
        "burnout",
        "fatigued",
        "broken",
        "empty",
        "thak gaya",
        "khatam",
        "aadhara",
        "टूटा हुआ",
        "थका हुआ",
        "खाली",
    )
    EMO_THEME_PRESSURED = (
        "pressure",
        "overwhelmed",
        "too much",
        "burden",
        "heavy",
        "stretched",
        "pushed",
        "expectations",
        "demands",
        "loaded",
        "bhaar",
        "jyada",
        "press the",
        "दबाव",
        "भार",
        "जिम्मेदारियाँ",
    )
    # Family / comparison markers (must enforce shaping)
    EMO_THEME_FAMILY = (
        "parents",
        "parent",
        "family",
        "comparing",
        "compare",
        "comparison",
        "disappoint",
        "disappointing",
        "gharwale",
        "mata",
        "pita",
        "मां",
        "पिता",
        "माता",
        "पिता",
    )

    # Advice-ban markers used during escalation to detect unwanted advice
    EMO_ADVICE_BAN = (
        "should",
        "try to",
        "best way",
        "you need",
        "you should",
        "you've got to",
        "having a healthy",
        "having a healthy life",
        "best thing",
    )

    # B3.3 Pushback markers: force a short non-advice acknowledgment
    PUSHBACK_MARKERS = (
        "annoys me",
        "tired of hearing",
        "don't give",
        "dont give",
        "stop saying",
        "i don't want",
        "i dont want",
        "please don't",
        "please dont",
        "don't give generic",
    )

    PUSHBACK_TEMPLATES = {
        "en": "Got it — I won’t push advice or fixes. That frustration makes sense. I’m here with you.",
        "hi": "Samajh gaya. Advice ya exercises nahi. Bas yeh frustrating feeling ko acknowledge kar raha hoon.",
    }

    EMO_OVERWHELM_MARKERS = (
        "spiral",
        "spiralling",
        "racing",
        "mind racing",
        "mind is racing",
        "can't switch off",
        "cant switch off",
        "switch off",
        "panic",
        "panic aa",
        "overwhelmed",
        "doom",
        "doom-scrolling",
        "doom scrolling",
        "on edge",
        "too much",
        "loop",
        "overthinking",
        "tension is building",
        "noisy mind",
        "brain nonstop",
        "dimag nonstop",
    )
    EMO_GUILT_MARKERS = (
        "guilt",
        "guilty",
        "shame",
        "ashamed",
        "lazy",
        "failure",
        "failing",
        "i am failing",
        "i'm failing",
        "behind",
        "falling behind",
        "procrastinat",
        "wasting time",
        "can't focus",
        "cant focus",
        "self-judg",
        "khud ko",
        "apne aap",
    )

    # Openers are small phrase pools; avoid consecutive reuse.
    EMO_OPENERS = {
        ("en", "A"): [
            "That sounds really heavy.",
            "That sounds like a lot to carry.",
            "That sounds hard right now.",
            "That sounds exhausting.",
        ],
        ("en", "B"): [
            "That sounds like a lot all at once.",
            "That sounds overwhelming.",
            "I hear you. That sounds like too much at once.",
        ],
        ("en", "C"): [
            "That sounds exhausting.",
            "I hear you. That sounds hard.",
            "That sounds like you’re carrying a lot.",
        ],
        ("en", "D"): [
            "That sounds heavy.",
            "I hear you.",
            "That sounds like a rough moment.",
        ],
        ("hi", "A"): [
            "मैं समझ सकता हूँ। यह भारी लग सकता है।",
            "मैं समझ सकता हूँ। यह सच में मुश्किल लग रहा है।",
            "ऐसा महसूस होना समझ में आता है।",
        ],
        ("hi", "B"): [
            "मैं समझ सकता हूँ। लग रहा है कि बहुत कुछ एक साथ आ रहा है।",
            "मैं समझ सकता हूँ। जब सब कुछ एक साथ हो, दिमाग तेज़ चलने लगता है।",
            "मैं समझ सकता हूँ। यह ओवरलोड वाकई थका देता है।",
        ],
        ("hi", "C"): [
            "मैं समझ सकता हूँ। यह अपराधबोध थका देने वाला हो सकता है।",
            "मैं समझ सकता हूँ। अटका हुआ महसूस करना नाकामी नहीं है।",
            "मैं समझ सकता हूँ। खुद पर गुस्सा आना समझ में आता है।",
        ],
        ("hi", "D"): [
            "मैं समझ सकता हूँ।",
            "मैं समझ सकता हूँ। यह भारी लग रहा है।",
            "मैं समझ सकता हूँ। अभी इसे छोटा रखते हैं।",
        ],
        ("hinglish", "A"): [
            "I hear you.",
            "That sounds heavy.",
            "I hear you. That sounds hard.",
        ],
        ("hinglish", "B"): [
            "I hear you. Lag raha sab ek saath aa gaya.",
            "That sounds like a lot. Jab sab pile up ho jaye, dimag fast chalne lagta hai.",
            "I hear you. Yeh overload thaka deta hai.",
        ],
        ("hinglish", "C"): [
            "I hear you. Yeh guilt kaafi draining hota hai.",
            "That sounds hard. Stuck feel karna failure nahi hota.",
            "I hear you. Khud par gussa aana samajh aata hai.",
        ],
        ("hinglish", "D"): [
            "I hear you.",
            "That sounds heavy.",
            "I hear you. Thoda slow karte hain.",
        ],
    }

    EMO_ACTION_STEPS = {
        "en": [
            ("breath_426", "For the next 60 seconds, try 4-2-6 breathing: inhale 4, hold 2, exhale 6."),
            ("ground_321", "For the next minute, look around and name 3 things you see, 2 you can touch, and 1 sound you hear."),
            ("timer_10", "Set a 10-minute timer and do just the smallest next step, then stop."),
            ("write_3", "Write 3 quick lines: what’s on my mind, what’s in my control, and one tiny next step."),
            ("move_30", "Stand up, roll your shoulders once, and take 3 slow breaths."),
        ],
        "hi": [
            ("breath_426", "अगले 60 सेकंड के लिए 4-2-6 सांस लें: 4 गिनकर अंदर, 2 रोकें, 6 गिनकर धीरे-धीरे छोड़ें।"),
            ("ground_321", "अगले एक मिनट में 3 चीज़ें देखें, 2 चीज़ें छूकर महसूस करें, और 1 आवाज़ पर ध्यान दें।"),
            ("timer_10", "10 मिनट का टाइमर लगाइए और बस सबसे छोटा अगला कदम करिए, फिर रुक जाइए।"),
            ("write_3", "3 लाइन लिखिए: दिमाग में क्या है, मेरे कंट्रोल में क्या है, और एक छोटा अगला कदम।"),
            ("move_30", "खड़े होकर कंधे एक बार ढीले करें और 3 धीमी सांस लें।"),
        ],
        "hinglish": [
            ("breath_426", "Next 60 seconds ke liye 4-2-6 breathing try karo: 4 count inhale, 2 hold, 6 count exhale."),
            ("ground_321", "Next 1 minute: 3 cheezein dekho, 2 cheezein touch karke feel karo, aur 1 sound notice karo."),
            ("timer_10", "10-minute timer lagao aur bas smallest next step karo, phir stop."),
            ("write_3", "3 lines likho: dimaag mein kya hai, control mein kya hai, aur 1 tiny next step."),
            ("move_30", "Khade ho jao, shoulders relax karo, aur 3 slow breaths lo."),
        ],
    }

    @classmethod
    def _sentence_count(cls, text: str) -> int:
        if not text:
            return 0
        parts = [p.strip() for p in cls.SHAPE_SENTENCE_SPLIT_RE.split(text) if p.strip()]
        return sum(1 for p in parts if re.search(r"\w", p, flags=re.UNICODE))

    @classmethod
    def _is_explanatory_boilerplate(cls, text: str) -> bool:
        lower = text.strip().lower()
        return lower.startswith("here is a simple explanation") or lower.startswith("simple shabdon mein")

    @classmethod
    def _is_good_explanatory_target(cls, text: str) -> bool:
        # Definition + example in practice usually implies >= 2 sentences.
        if cls._is_explanatory_boilerplate(text):
            return False
        return cls._sentence_count(text) >= 2

    @classmethod
    def _split_sentences_keep_punct(cls, text: str):
        if not text:
            return []
        parts = [p.strip() for p in cls.SENTENCE_BOUNDARY_RE.split(text.strip()) if p.strip()]
        return parts or [text.strip()]

    @classmethod
    def _prompt_looks_hinglish(cls, prompt_lower: str) -> bool:
        return any(marker in prompt_lower for marker in cls.HINGLISH_MARKERS)

    @classmethod
    def _needs_emotional_action_shaping(cls, prompt_lower: str) -> bool:
        has_timebox = bool(cls.EMO_TIMEBOX_RE.search(prompt_lower)) or any(
            marker in prompt_lower for marker in cls.EMO_TIMEBOX_MARKERS
        )
        has_action_request = any(marker in prompt_lower for marker in cls.EMO_ACTION_REQUEST_MARKERS)
        return has_timebox and has_action_request

    @classmethod
    def _has_action_step(cls, response: str, lang: str) -> bool:
        if not response:
            return False
        if lang == "hi":
            return any(marker in response for marker in cls.EMO_ACTION_RESPONSE_MARKERS_HI)
        lower = response.lower()
        return any(marker in lower for marker in cls.EMO_ACTION_RESPONSE_MARKERS_EN)

    @classmethod
    def _emotional_lang_mode(cls, prompt: str, lang: str) -> str:
        if lang == "hi":
            return "hi"
        prompt_lower = prompt.lower()
        if cls._prompt_looks_hinglish(prompt_lower):
            return "hinglish"
        return "en"

    @classmethod
    def _looks_like_emotional_template(cls, text: str, lang_mode: str) -> bool:
        if not text:
            return True
        cleaned = " ".join(text.strip().split())
        lower = cleaned.lower()
        if lang_mode == "hi":
            if cleaned == cls.EMO_FALLBACK_HI:
                return True
            if cleaned == "Main samajh raha hoon. Aap batao kis cheez mein help chahiye, main poori koshish karunga.":
                return True
            return False
        # en / hinglish (latin)
        if lower == cls.EMO_FALLBACK_EN:
            return True
        if lower == cls.CONV_FALLBACK_EN:
            return True
        # Catch the common templated prefix even if punctuation differs.
        return lower.startswith("i hear you. you're not alone. it's okay to feel this way")

    @classmethod
    def _select_emotional_skeleton(cls, prompt_lower: str) -> str:
        if cls._needs_emotional_action_shaping(prompt_lower):
            return "D"
        if any(m in prompt_lower for m in cls.EMO_OVERWHELM_MARKERS):
            return "B"
        if any(m in prompt_lower for m in cls.EMO_GUILT_MARKERS):
            return "C"
        return "A"

    @classmethod
    def _detect_emotional_theme(cls, prompt_lower: str) -> Optional[str]:
        """
        Classify the emotional theme from the prompt.
        Returns one of: "lost", "anxious", "drained", "pressured", or None
        """
        if any(m in prompt_lower for m in cls.EMO_THEME_LOST):
            return "lost"
        if any(m in prompt_lower for m in cls.EMO_THEME_ANXIOUS):
            return "anxious"
        if any(m in prompt_lower for m in cls.EMO_THEME_DRAINED):
            return "drained"
        if any(m in prompt_lower for m in cls.EMO_THEME_PRESSURED):
            return "pressured"
        if any(m in prompt_lower for m in cls.EMO_THEME_FAMILY):
            return "family"
        return None

    @classmethod
    def _is_parroting(cls, user: str, response: str) -> bool:
        """
        Cheap bigram overlap parroting detector.
        Returns True if >=50% of response bigrams are present in user bigrams
        or the response starts with obvious parroting phrases.
        """
        if not user or not response:
            return False

        u = user.lower()
        r = response.lower()

        # Quick phrase starts that indicate parroting
        starts = ("i don't want", "you said", "you said:", '"')
        if any(r.strip().startswith(s) for s in starts):
            return True

        def bigrams(text: str):
            toks = [t for t in re.findall(r"\w+", text)]
            return [" ".join(toks[i : i + 2]) for i in range(max(0, len(toks) - 1))]

        ub = set(bigrams(u))
        rb = bigrams(r)
        if not rb:
            return False
        overlap = sum(1 for b in rb if b in ub)
        frac = overlap / len(rb)
        return frac >= 0.5

    def _render_pushback_ack(self, lang: str) -> str:
        lang_short = (lang or "en").split("-")[0]
        return self.PUSHBACK_TEMPLATES.get(lang_short, self.PUSHBACK_TEMPLATES["en"])

    @classmethod
    def _has_resignation_markers(cls, prompt_lower: str) -> bool:
        """
        Detect if the user is expressing resignation, futility, or stuckness.
        B3.2 escalation trigger condition B.
        """
        return any(m in prompt_lower for m in cls.EMO_RESIGNATION_MARKERS)

    def _check_escalation_conditions(
        self, prompt_lower: str, intent: str, current_theme: Optional[str]
    ) -> bool:
        """
        Check if B3.2 emotional escalation conditions are all met.
        
        Conditions:
        A. Continuity: same session (implicit in instance state)
        B. Repetition signal: same theme OR resignation markers present
        C. Intent must be emotional
        """
        # Must be emotional intent
        if intent != "emotional":
            return False

        # Condition A: same session - implicitly true (instance state)
        # Condition B: theme continuity + repetition signal
        if self._emo_theme is None:
            # First emotional turn in session - track theme, no escalation yet
            self._emo_theme = current_theme
            return False

        # Check if theme matches
        theme_matches = (self._emo_theme == current_theme) and current_theme is not None
        has_resignation = self._has_resignation_markers(prompt_lower)

        # Check skeleton repetition
        skeleton_repeated = (
            len(self._emo_skeleton_history) >= 2
            and self._emo_skeleton_history[-1] == self._emo_skeleton_history[-2]
        )

        # Escalation condition met if:
        # - Same theme + skeleton repeated, OR
        # - Has resignation markers
        escalation_triggered = (theme_matches and skeleton_repeated) or has_resignation

        # Update theme for next turn
        if current_theme is not None:
            self._emo_theme = current_theme

        return escalation_triggered

    @classmethod
    def _get_next_escalation_skeleton(cls, current_skeleton: str) -> str:
        """
        Return the next skeleton in the escalation sequence.
        Escalation paths (per B3.2 spec):
            A → B
            B → C
            C → C (stays at C)
            D → D (never escalate from action)
        
        Returns the next skeleton; if no escalation path, returns current.
        """
        escalation_map = {
            "A": "B",
            "B": "C",
            "C": "C",
            "D": "D",
        }
        return escalation_map.get(current_skeleton, current_skeleton)

    @classmethod
    def _emotional_context_hint(cls, prompt_lower: str, lang_mode: str) -> str:
        # Keep this subtle and short (no stacked metaphors).
        if any(x in prompt_lower for x in ("sleep", "insomnia", "night", "switch off", "nind", "raat")):
            return {
                "en": "When the mind won’t switch off, everything feels louder.",
                "hi": "जब दिमाग बंद नहीं होता, तो सब कुछ ज़्यादा भारी लग सकता है।",
                "hinglish": "Jab dimag switch off na ho, sab aur heavy lagta hai.",
            }.get(lang_mode, "")
        if any(x in prompt_lower for x in ("exam", "interview", "upsc", "procrastinat")):
            return {
                "en": "Pressure like this can make the mind feel noisy.",
                "hi": "ऐसा दबाव दिमाग को बहुत बेचैन कर देता है।",
                "hinglish": "Aisa pressure dimag ko noisy bana deta hai.",
            }.get(lang_mode, "")
        if any(x in prompt_lower for x in ("family", "gharwale", "pressure", "career", "money")):
            return {
                "en": "Family and career pressure together can feel suffocating.",
                "hi": "परिवार और करियर का दबाव एक साथ बहुत भारी लग सकता है।",
                "hinglish": "Family aur career ka pressure ek saath heavy ho jata hai.",
            }.get(lang_mode, "")
        if any(x in prompt_lower for x in ("lonely", "alone")):
            return {
                "en": "Loneliness can drain your energy quietly.",
                "hi": "अकेलापन धीरे-धीरे ऊर्जा खींच लेता है।",
                "hinglish": "Loneliness quietly energy drain kar deta hai.",
            }.get(lang_mode, "")
        return ""

    def _emo_choose_opener(self, lang_mode: str, skeleton: str) -> str:
        key = (lang_mode, skeleton)
        pool = self.EMO_OPENERS.get(key, [])
        if not pool:
            return "I hear you." if lang_mode != "hi" else "मैं समझ सकता हूँ।"

        last = self._emo_last_opener.get(key)
        if len(pool) == 1:
            chosen = pool[0]
        else:
            # Rotate deterministically: pick the first opener not equal to last.
            chosen = next((o for o in pool if o != last), pool[0])
        self._emo_last_opener[key] = chosen
        return chosen

    def _emo_choose_action_step(self, prompt_lower: str, lang_mode: str) -> tuple:
        pool = self.EMO_ACTION_STEPS.get(lang_mode if lang_mode in self.EMO_ACTION_STEPS else "en", [])
        if not pool:
            return "breath_426", "For the next 60 seconds, try 4-2-6 breathing: inhale 4, hold 2, exhale 6."

        # Prefer a matching action for common situations.
        preferred_ids = []
        if any(x in prompt_lower for x in ("procrastinat", "reset", "10-minute", "10 minute", "tonight")):
            preferred_ids.extend(["timer_10", "write_3", "breath_426"])
        if any(x in prompt_lower for x in ("panic", "spiral", "racing", "overthinking", "mind")):
            preferred_ids.extend(["breath_426", "ground_321"])
        if any(x in prompt_lower for x in ("sleep", "insomnia", "night", "nind", "raat")):
            preferred_ids.extend(["ground_321", "breath_426", "write_3"])

        # Drop last action if possible.
        last_id = self._emo_last_action_id

        candidates = pool
        if preferred_ids:
            pref = [item for item in pool if item[0] in preferred_ids]
            if pref:
                candidates = pref

        chosen = next((item for item in candidates if item[0] != last_id), candidates[0])
        self._emo_last_action_id = chosen[0]
        return chosen[0], chosen[1]

    def _render_emotional_skeleton(self, prompt: str, lang_mode: str, skeleton: str) -> tuple:
        prompt_lower = prompt.lower()
        opener = self._emo_choose_opener(lang_mode, skeleton)
        hint = self._emotional_context_hint(prompt_lower, lang_mode)

        if skeleton == "D":
            _, action = self._emo_choose_action_step(prompt_lower, lang_mode)
            if lang_mode == "hi":
                line1 = opener
                line2 = action
                return (f"{line1} {line2}").strip(), "D"
            return (f"{opener} {action}").strip(), "D"

        if skeleton == "B":
            if lang_mode == "hi":
                parts = [opener]
                if hint:
                    parts.append(hint)
                parts.append("अभी बस इस पल को थोड़ा धीमा करते हैं। आपको सब कुछ एक साथ नहीं सुलझाना है।")
                parts.append("अगर चाहें, बताइए अभी सबसे ज़्यादा क्या भारी लग रहा है।")
                return " ".join(parts).strip(), "B"
            if lang_mode == "hinglish":
                parts = [opener]
                if hint:
                    parts.append(hint)
                parts.append("Abhi bas is moment ko slow karte hain. Sab kuch ek saath solve karna zaroori nahi.")
                parts.append("Agar chaho, batao abhi sabse zyada heavy kya lag raha hai.")
                return " ".join(parts).strip(), "B"
            parts = [opener]
            if hint:
                parts.append(hint)
            parts.append("Right now, let’s slow this moment down. You don’t have to solve everything at once.")
            parts.append("If you want, tell me what feels heaviest right now.")
            return " ".join(parts).strip(), "B"

        if skeleton == "C":
            if lang_mode == "hi":
                parts = [opener]
                if hint:
                    parts.append(hint)
                parts.append("इसका मतलब नहीं कि आप कमजोर हैं या फेल हो रहे हैं।")
                parts.append("अभी के लिए बस एक छोटा सा व्यावहारिक कदम चुनते हैं।")
                return " ".join(parts).strip(), "C"
            if lang_mode == "hinglish":
                parts = [opener]
                if hint:
                    parts.append(hint)
                parts.append("Iska matlab yeh nahi ki tum fail ho rahe ho. It means you care.")
                parts.append("Abhi ke liye bas ek chhota practical step pick karte hain.")
                return " ".join(parts).strip(), "C"
            parts = [opener]
            if hint:
                parts.append(hint)
            parts.append("It doesn’t mean you’re failing. It usually means you care and you’re stretched.")
            parts.append("For now, let’s keep it practical and small.")
            return " ".join(parts).strip(), "C"

        # Skeleton A (default gentle validation).
        if lang_mode == "hi":
            parts = [opener]
            if hint:
                parts.append(hint)
            parts.append("अभी इसे छोटा रखते हैं। आपको सब कुछ तुरंत ठीक नहीं करना है।")
            parts.append("अगर चाहें, थोड़ा बताइए कि किस बात ने इसे इतना भारी बना दिया।")
            return " ".join(parts).strip(), "A"
        if lang_mode == "hinglish":
            parts = [opener]
            if hint:
                parts.append(hint)
            parts.append("Abhi isko chhota rakhte hain. Sab kuch turant fix karna zaroori nahi.")
            parts.append("Agar chaho, batao kis cheez ne isko sabse zyada heavy bana diya.")
            return " ".join(parts).strip(), "A"
        parts = [opener]
        if hint:
            parts.append(hint)
        parts.append("For now, let’s keep it small. You don’t have to fix everything immediately.")
        parts.append("If you want, tell me what’s been weighing on you the most.")
        return " ".join(parts).strip(), "A"

    @classmethod
    def _explanatory_constraints(cls, prompt: str) -> dict:
        lower = prompt.lower()
        max_lines = None

        m = cls.EXPL_MAX_LINES_RE.search(lower)
        if m:
            max_lines = max(int(m.group(1)), int(m.group(2)))
        m = cls.EXPL_LINES_MAX_RE.search(lower)
        if m:
            max_lines = int(m.group(1))
        if ("3-4 lines" in lower) or ("3–4 lines" in lower) or ("3 to 4 lines" in lower):
            max_lines = 4
        if "keep it short" in lower or "keep it brief" in lower:
            max_lines = max_lines or 3

        wants_example = any(marker in lower for marker in ("example", "analogy", "using")) or (
            "उदाहरण" in prompt or "जैसे" in prompt
        )
        english_last = any(marker in lower for marker in cls.EXPL_ENGLISH_LAST_MARKERS)
        hindi_first = any(marker in lower for marker in cls.EXPL_HINDI_FIRST_MARKERS) or (
            "हिंदी पहले" in prompt or "पहले हिंदी" in prompt or "हिन्दी पहले" in prompt or "पहले हिन्दी" in prompt
        )
        no_jargon = any(marker in lower for marker in cls.EXPL_NO_JARGON_MARKERS)
        wants_lines = "line" in lower or "lines" in lower or "लाइनों" in prompt

        return {
            "max_lines": max_lines,
            "wants_example": wants_example,
            "english_last": english_last,
            "hindi_first": hindi_first,
            "no_jargon": no_jargon,
            "wants_lines": wants_lines,
        }

    @classmethod
    def _hindi_summary_for_topics(cls, topic_tokens: set) -> str:
        if "upi" in topic_tokens:
            return "UPI ka matlab hai phone se bank-to-bank payment turant karna."
        if "inflation" in topic_tokens:
            return "महंगाई का मतलब है समय के साथ चीज़ों की कीमतें बढ़ना।"
        if "credit_score" in topic_tokens or ("credit" in topic_tokens and "score" in topic_tokens):
            return "Credit score bank ka trust-score hota hai jo repayment history par based hota hai."
        if "encryption" in topic_tokens or "https" in topic_tokens:
            return "Encryption ka matlab hai data ko aise code mein badalna ki bina key ke na padha ja sake."
        if "http" in topic_tokens and "https" in topic_tokens:
            return "HTTP simple hota hai, HTTPS mein encryption hota hai."
        if "stress_test" in topic_tokens:
            return "Stress test ka matlab hai system ko heavy load dekar limits check karna."
        if "cache" in topic_tokens:
            return "Caching ka matlab hai frequently used cheez ko paas rakhna taaki fast mile."
        if "burnout" in topic_tokens:
            return "Burnout ka matlab hai long time stress se thak jaana aur energy khatam ho jana."
        return ""

    @classmethod
    def _english_summary_for_topics(cls, topic_tokens: set) -> str:
        if "upi" in topic_tokens:
            return "English: UPI lets you transfer money instantly between bank accounts using your phone."
        if "inflation" in topic_tokens:
            return "English: Inflation means prices rise over time, so the same money buys less."
        if "credit_score" in topic_tokens or ("credit" in topic_tokens and "score" in topic_tokens):
            return "English: A credit score is a trust number based on your repayment history."
        if "encryption" in topic_tokens or "https" in topic_tokens:
            return "English: Encryption scrambles data so only someone with the right key can read it."
        if "http" in topic_tokens and "https" in topic_tokens:
            return "English: HTTPS encrypts the connection; plain HTTP does not."
        if "stress_test" in topic_tokens:
            return "English: A stress test pushes a system with heavy load to find breaking points."
        if "cache" in topic_tokens:
            return "English: Caching keeps frequently used data closer so it can be served faster."
        if "burnout" in topic_tokens:
            return "English: Burnout is long-term exhaustion from prolonged stress or overwork."
        return ""

    @classmethod
    def _shape_explanatory(cls, prompt: str, response: str) -> str:
        if not response:
            return response

        constraints = cls._explanatory_constraints(prompt)
        out = response.strip()

        # If requested, ensure a Hindi-first response (when we can provide a safe summary).
        if constraints.get("hindi_first"):
            topic_tokens = cls._extract_topic_tokens(prompt)
            summary_hi = cls._hindi_summary_for_topics(topic_tokens)
            if summary_hi:
                # If output doesn't start with Devanagari, prepend a Hindi summary line.
                head = out[:60]
                if head and (not cls.DEVANAGARI_RE.search(head)):
                    out = (summary_hi + "\n" + out).strip()

        # Enforce line/sentence bounds if explicitly requested.
        max_lines = constraints.get("max_lines")
        if max_lines:
            sents = cls._split_sentences_keep_punct(out)
            sents = sents[:max_lines]
            joiner = "\n" if constraints.get("wants_lines") else " "
            out = joiner.join(sents).strip()

        # Ensure an English last line if requested and we can produce a safe summary.
        if constraints.get("english_last"):
            lines = out.splitlines() if out else []
            last = lines[-1] if lines else out
            if last and (not cls.LATIN_RE.search(last)):
                summary = cls._english_summary_for_topics(cls._extract_topic_tokens(prompt))
                if summary:
                    out = (out + "\n" + summary).strip()

        return out

    @classmethod
    def _is_explanatory_on_topic(cls, prompt: str, response: str) -> bool:
        """
        Micro quality check: explanation should be about the asked concept.
        This is a cheap keyword/topic overlap gate (not embeddings).
        """
        p_tokens = cls._extract_topic_tokens(prompt)
        if not p_tokens:
            # If the prompt has no extractable topic tokens, don't block on-topic checks.
            return True
        r_tokens = cls._extract_topic_tokens(response)
        if not r_tokens:
            return False
        return cls._is_retrieval_topic_safe(prompt, response)

    @classmethod
    def _needs_explanatory_regen(cls, prompt: str, response: str) -> bool:
        if not response:
            return True
        constraints = cls._explanatory_constraints(prompt)
        if cls._is_explanatory_boilerplate(response):
            return True
        if cls._sentence_count(response) < 2:
            return True
        if constraints.get("wants_example"):
            lower = response.lower()
            if not any(marker in lower for marker in cls.EXPL_EXAMPLE_MARKERS):
                # The example might be implicit, but if user explicitly asked for one, be strict.
                return True
        return False

    def _model_generate_cleaned(self, conditioned_prompt: str, max_new_tokens: int) -> str:
        inputs = self.tokenizer(
            conditioned_prompt,
            return_tensors="pt",
            truncation=True,
            max_length=128,
        ).to(self.device)

        output_ids = self.model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            bad_words_ids=self.bad_words_ids,
            num_beams=4,
            early_stopping=True,
            no_repeat_ngram_size=3,
            repetition_penalty=1.1,
        )

        decoded = self.tokenizer.decode(
            output_ids[0],
            skip_special_tokens=True,
        )
        return normalize_output(decoded)

    def _build_explanatory_shape_prompt(self, prompt: str, conditioned_prompt: str) -> str:
        constraints = self._explanatory_constraints(prompt)
        extra = []
        extra.append("Give a one-line definition, then one concrete example.")
        if constraints.get("no_jargon"):
            extra.append("Avoid jargon; use simple words.")
        if constraints.get("max_lines"):
            extra.append(f"Keep it within {constraints['max_lines']} lines.")
        if constraints.get("english_last"):
            extra.append("Make the last line English.")
        if constraints.get("hindi_first"):
            extra.append("Start with Hindi, then English.")
        if self._prompt_looks_hinglish(prompt.lower()):
            extra.append("Use simple Hinglish (mix Hindi and English naturally).")

        suffix = " ".join(extra).strip()
        if not suffix:
            return conditioned_prompt
        return f"{conditioned_prompt}\n\n{suffix}"

    def _post_process_response(
        self,
        prompt: str,
        intent: str,
        lang: str,
        conditioned_prompt: str,
        text: str,
        meta: dict,
        max_new_tokens: int,
    ):
        """
        Deterministic shaping + micro quality checks.
        This runs after intent detection and after (optional) memory retrieval.
        """
        if not text:
            return text, meta

        prompt_lower = prompt.lower()

        # Step 1: Persona v1 emotional shaping (bounded skeletons + anti-repetition).
        if intent == "emotional":
            # Never override a safety refusal that was enforced by policies.
            if text.strip() == REFUSAL_FALLBACK:
                return text, meta

            lang_mode = self._emotional_lang_mode(prompt, lang)
            force_action = self._needs_emotional_action_shaping(prompt_lower)
            desired = self._select_emotional_skeleton(prompt_lower)
            eligible = ["A"]
            if any(m in prompt_lower for m in self.EMO_OVERWHELM_MARKERS):
                eligible.append("B")
            if any(m in prompt_lower for m in self.EMO_GUILT_MARKERS):
                eligible.append("C")
            if force_action:
                eligible.append("D")

            # B3.2 Escalation detection
            current_theme = self._detect_emotional_theme(prompt_lower)
            escalation_triggered = self._check_escalation_conditions(
                prompt_lower, intent, current_theme
            )

            with self._emo_lock:
                skeleton = desired if desired in eligible else eligible[0]

                # B3.2 Escalation: if conditions met, move to next skeleton in sequence
                if escalation_triggered and skeleton != "D":
                    next_skeleton = self._get_next_escalation_skeleton(skeleton)
                    # Force A->B when escalation persists, even if B wasn't originally eligible
                    if next_skeleton != skeleton:
                        # allow escalation override even if not in eligible
                        skeleton = next_skeleton
                        self._emo_escalation_active = True

                # B3.1 Rotation rule: avoid repeating the same skeleton twice in a row
                # when there is another eligible option (except forced D), unless escalation active.
                if (
                    skeleton != "D"
                    and not self._emo_escalation_active
                    and skeleton == self._emo_last_skeleton
                    and len(eligible) > 1
                ):
                    alt = next((s for s in eligible if s != self._emo_last_skeleton), skeleton)
                    skeleton = alt

                # Track skeleton history for escalation detection
                self._emo_skeleton_history.append(skeleton)
                if len(self._emo_skeleton_history) > 5:
                    self._emo_skeleton_history.pop(0)

                # If this turn explicitly indicates a family theme, latch it for the session
                if current_theme == "family":
                    self._family_theme_latched = True

                # Render the chosen skeleton (hard contract when escalation or family theme)
                shaped_text, used = self._render_emotional_skeleton(prompt, lang_mode, skeleton)
                self._emo_last_skeleton = used

                # Enforce hard contract: if escalation active or family theme, disallow raw/unshaped model outputs
                # If the rendered text looks advicey or contains banned phrases, escalate to C (shared stillness)
                if self._emo_escalation_active or (current_theme == "family"):
                    # Ensure shaped_text contains empathy markers (simple heuristic: starts with an opener)
                    lower_shaped = (shaped_text or "").lower()
                    advice_hit = any(b in lower_shaped for b in self.EMO_ADVICE_BAN)
                    if advice_hit:
                        # Re-render as skeleton C (shared stillness)
                        shaped_text, used = self._render_emotional_skeleton(prompt, lang_mode, "C")
                        self._emo_last_skeleton = used
                        meta_override_escalation = True
                    else:
                        meta_override_escalation = True
                else:
                    meta_override_escalation = False

            meta = dict(meta)
            meta["shaped"] = True
            # Tag escalation separately for visibility
            if escalation_triggered or meta_override_escalation:
                meta["shape"] = "emotional_escalation"
                meta["escalation_active"] = True
                meta["emotional_theme"] = current_theme
            else:
                meta["shape"] = "emotional_skeleton"
            meta["emotional_skeleton"] = used
            meta["emotional_lang"] = lang_mode

            # Absolute no-advice gate: if escalation active and shaped_text still contains advice markers,
            # force shared stillness (C) and update meta.
            lower_final = (shaped_text or "").lower()
            if meta.get("escalation_active") and any(b in lower_final for b in self.EMO_ADVICE_BAN):
                shaped_text, used = self._render_emotional_skeleton(prompt, lang_mode, "C")
                meta["shape"] = "emotional_escalation"
                meta["escalation_active"] = True
                meta["emotional_skeleton"] = used

            return shaped_text, meta

        # Step 2 + Step 3: explanatory shaping + topic micro-check + contract-driven regen.
        if intent == "explanatory":
            shaped = self._shape_explanatory(prompt, text)
            if shaped != text:
                meta = dict(meta)
                meta["shaped"] = True
                meta["shape"] = meta.get("shape") or "explanatory_constraints"
            text = shaped

            on_topic = self._is_explanatory_on_topic(prompt, text)
            needs_regen = (not on_topic) or self._needs_explanatory_regen(prompt, text)

            if needs_regen:
                # Try a stricter semantic memory hit first (non-contaminating).
                semantic_hit = self.memory.lookup_semantic(
                    conditioned_prompt,
                    min_score=0.40,
                    target_predicate=self._is_good_explanatory_target,
                ) or self.memory.lookup_semantic(conditioned_prompt, min_score=0.40)

                if semantic_hit and self._is_retrieval_topic_safe(prompt, semantic_hit):
                    recovered = normalize_output(semantic_hit)
                    recovered_final = apply_response_policies(recovered, intent=intent, lang=lang, prompt=prompt)
                    recovered_final = self._shape_explanatory(prompt, recovered_final)
                    if self._is_explanatory_on_topic(prompt, recovered_final) and (not self._needs_explanatory_regen(prompt, recovered_final)):
                        new_meta = {"source": "memory_semantic", "post_rescue": True, "post_rescue_reason": "shape_or_topic"}
                        return recovered_final, new_meta

                # One controlled re-generation pass with an explicit structure contract.
                shaped_prompt = self._build_explanatory_shape_prompt(prompt, conditioned_prompt)
                regenerated = self._model_generate_cleaned(shaped_prompt, max_new_tokens=max_new_tokens)
                regenerated_final = apply_response_policies(regenerated, intent=intent, lang=lang, prompt=prompt)
                regenerated_final = self._shape_explanatory(prompt, regenerated_final)
                if self._is_explanatory_on_topic(prompt, regenerated_final) and (not self._needs_explanatory_regen(prompt, regenerated_final)):
                    meta = dict(meta)
                    meta["post_regen"] = True
                    meta["post_regen_prompt"] = "shape_contract"
                    return regenerated_final, meta

            return text, meta

        # Default: no shaping.
        return text, meta

    def __init__(self, model_dir: str = "artifacts/alignment_lora/final"):
        loader = ModelLoader(model_dir)
        self.model, self.tokenizer = loader.load()
        self.memory = AlignmentMemory()

        self.device = next(self.model.parameters()).device

        self.model.config.decoder_start_token_id = self.tokenizer.pad_token_id
        self.bad_words_ids = self._build_sentinel_blocklist()
        self.model.eval()

        # Session-scoped persona state for bounded emotional variety.
        self._emo_lock = threading.Lock()
        self._emo_last_skeleton = None
        self._emo_last_opener = {}
        self._emo_last_action_id = None

        # B3.2 Emotional Escalation Rule: track session emotional context
        self._emo_theme = None  # One of: "lost", "anxious", "drained", "pressured", None
        self._emo_skeleton_history = []  # Track last few skeletons for escalation continuity
        self._emo_escalation_active = False  # Flag: are we in escalation mode?
        # Session-level family theme latch: once a family theme is detected in-session,
        # keep it active for the remainder of the session and enforce shaping.
        self._family_theme_latched = False

        self.voice_state = SessionVoiceState(
            rotation_memory=RotationMemory()
        )
    def _build_sentinel_blocklist(self):
        vocab = self.tokenizer.get_vocab()
        sentinel_ids = sorted(
            token_id for token, token_id in vocab.items() if "<extra_id_" in token
        )
        return [[token_id] for token_id in sentinel_ids]

    def _prepare_prompt(self, prompt: str) -> str:
        text = prompt.strip()
        match = self.PREFIX_RE.match(text)
        if match:
            text = match.group(2).strip()

        intent = detect_intent(text)
        prefix = {
            "emotional": "empathy",
            "factual": "fact",
            "explanatory": "explain",
            "uncertain": "uncertain",
            "refusal": "refusal",
            "conversational": "empathy",
        }.get(intent, "empathy")
        return f"{prefix}: {text}"

    def _pack(self, text: str, meta: dict, return_meta: bool):
        return (text, meta) if return_meta else text

    def _factual_floor_answer(self, prompt: str, lang: str):
        lower = prompt.lower()

        # Lightweight deterministic conversion for simple time-unit facts.
        match_hours = re.search(r"\b(\d+)\s*(ghante|ghanta|hour|hours)\b", lower)
        if match_hours and re.search(r"\b(minute|minutes|min)\b", lower):
            minutes = int(match_hours.group(1)) * 60
            return f"{minutes} minutes.", "unit_hours_to_minutes"
        match_hours_hi = re.search(r"(\d+)\s*(घंटे|घंटा)", prompt)
        if match_hours_hi and re.search(r"(मिनट|minute|minutes|min)", prompt, re.IGNORECASE):
            minutes = int(match_hours_hi.group(1)) * 60
            if lang == "hi":
                return f"{minutes} मिनट।", "unit_hours_to_minutes"
            return f"{minutes} minutes.", "unit_hours_to_minutes"

        if "dns" in lower and ("stand for" in lower or "full form" in lower):
            return "Domain Name System.", "acronym_dns"

        if "http" in lower and ("stand for" in lower or "stands for" in lower or "full form" in lower):
            return "HTTP stands for HyperText Transfer Protocol.", "acronym_http"

        if "https" in lower and ("stand for" in lower or "stands for" in lower or "full form" in lower):
            return "HTTPS stands for HyperText Transfer Protocol Secure.", "acronym_https"

        if "cpu" in lower and ("stand for" in lower or "stands for" in lower or "full form" in lower):
            return "CPU stands for Central Processing Unit.", "acronym_cpu"

        if "upi" in lower and ("stand for" in lower or "stands for" in lower or "full form" in lower):
            return "UPI stands for Unified Payments Interface.", "acronym_upi"

        if "rbi" in lower and ("stand for" in lower or "stands for" in lower or "full form" in lower):
            return "RBI stands for Reserve Bank of India.", "acronym_rbi"

        if "ifsc" in lower and ("stand for" in lower or "stands for" in lower or "full form" in lower):
            return "IFSC stands for Indian Financial System Code.", "acronym_ifsc"

        if ("independence day" in lower and ("india" in lower or "भारत" in prompt)) or ("स्वतंत्रता दिवस" in prompt):
            if lang == "hi":
                return "भारत का स्वतंत्रता दिवस 15 अगस्त 1947 है।", "india_independence_day"
            return "India's Independence Day is 15 August 1947.", "india_independence_day"

        if ("republic day" in lower and ("india" in lower or "भारत" in prompt)) or ("गणतंत्र दिवस" in prompt):
            if lang == "hi":
                return "भारत का गणतंत्र दिवस 26 जनवरी को होता है।", "india_republic_day"
            return "India's Republic Day is on 26 January.", "india_republic_day"

        if ("capital of india" in lower) or ("भारत की राजधानी" in prompt) or ("capital" in lower and "india" in lower):
            if lang == "hi":
                return "नई दिल्ली भारत की राजधानी है।", "india_capital"
            return "New Delhi is the capital of India.", "india_capital"

        if ("japan" in lower or "जापान" in prompt) and ("currency" in lower or "मुद्रा" in prompt):
            if lang == "hi":
                return "जापान की मुद्रा जापानी येन है।", "currency_japan"
            return "The currency of Japan is the Japanese Yen.", "currency_japan"

        if ("moon" in lower or "chand" in lower or "चंद्रमा" in prompt or "चाँद" in prompt) and (
            "first" in lower or "pehla" in lower or "insaan" in lower or "human" in lower or "पहला" in prompt
        ):
            if lang == "hi":
                return "चंद्रमा पर पहला इंसान नील आर्मस्ट्रॉन्ग था।", "moon_first_human"
            return "Neil Armstrong was the first human on the Moon.", "moon_first_human"

        if ("constitution" in lower or "संविधान" in prompt) and ("india" in lower or "भारत" in prompt):
            if "when" in lower or "kab" in lower or "कब" in prompt or "लागू" in prompt:
                if lang == "hi":
                    return "भारत का संविधान 26 जनवरी 1950 को लागू हुआ।", "india_constitution_effective"
                return "The Constitution of India came into effect on 26 January 1950.", "india_constitution_effective"

        if ("chemical formula" in lower or "formula" in lower) and "water" in lower:
            if lang == "hi":
                return "H2O पानी का रासायनिक सूत्र है।", "chem_water_h2o"
            return "Water's molecular formula is H2O.", "chem_water_h2o"

        if ("closest" in lower and "sun" in lower and "planet" in lower) or ("closest planet" in lower and "sun" in lower):
            if lang == "hi":
                return "सूर्य के सबसे नज़दीक ग्रह बुध है।", "planet_closest_to_sun"
            return "Mercury is the closest planet to the Sun.", "planet_closest_to_sun"

        if ("red planet" in lower) or (
            ("planet" in lower or "ग्रह" in prompt) and ("red" in lower or "लाल" in prompt)
        ):
            if lang == "hi":
                return "वह ग्रह मंगल है।", "planet_red"
            return "It is Mars.", "planet_red"

        if "penicillin" in lower and ("who" in lower or "discovered" in lower):
            if lang == "hi":
                return "पेनिसिलिन की खोज अलेक्ज़ेंडर फ्लेमिंग ने की।", "discover_penicillin"
            return "Alexander Fleming discovered penicillin.", "discover_penicillin"

        if ("largest ocean" in lower) or (
            ("ocean" in lower or "महासागर" in prompt) and ("largest" in lower or "सबसे बड़ा" in prompt)
        ):
            if lang == "hi":
                return "प्रशांत महासागर सबसे बड़ा है।", "ocean_largest"
            return "Pacific Ocean.", "ocean_largest"

        if ("national anthem" in lower or "राष्ट्रीय गान" in prompt) and (
            "india" in lower or "भारत" in prompt
        ):
            if lang == "hi":
                return "राष्ट्रीय गान रवींद्रनाथ टैगोर ने लिखा।", "india_national_anthem_author"
            return "Rabindranath Tagore wrote India's national anthem.", "india_national_anthem_author"

        if ("national animal" in lower or "राष्ट्रीय पशु" in prompt) and ("india" in lower or "भारत" in prompt):
            if lang == "hi":
                return "भारत का राष्ट्रीय पशु बाघ (रॉयल बंगाल टाइगर) है।", "india_national_animal"
            return "India's national animal is the Bengal tiger.", "india_national_animal"

        if ("evolution" in lower and "natural selection" in lower) or ("प्राकृतिक चयन" in prompt):
            if lang == "hi":
                return "प्राकृतिक चयन द्वारा विकास का सिद्धांत चार्ल्स डार्विन से जुड़ा है।", "evolution_natural_selection"
            return "Charles Darwin proposed evolution by natural selection.", "evolution_natural_selection"

        if "french revolution" in lower and ("kis saal" in lower or "which year" in lower or "saal" in lower):
            return "It began in 1789.", "history_french_revolution_start"

        if ("organ" in lower and "pumps blood" in lower) or ("blood" in lower and "pump" in lower):
            if lang == "hi":
                return "दिल (हृदय) रक्त पंप करता है।", "bio_heart_pumps_blood"
            return "The heart pumps blood through the body.", "bio_heart_pumps_blood"

        if ("parliament" in lower or "सदन" in prompt) and ("do" in lower or "two" in lower or "दो" in prompt):
            if ("lok sabha" in lower) or ("rajya sabha" in lower) or ("संसद" in prompt) or ("parliament" in lower):
                if lang == "hi":
                    return "भारतीय संसद के दो सदन हैं: लोकसभा और राज्यसभा।", "india_parliament_two_houses"
                return "The two Houses are the Lok Sabha and the Rajya Sabha.", "india_parliament_two_houses"

        return None, None

    @torch.no_grad()
    def generate(self, prompt: str, max_new_tokens: int = 64, return_meta: bool = False):
        intent = detect_intent(prompt)
        lang = detect_language(prompt)
        conditioned_prompt = self._prepare_prompt(prompt)
        # Early family-theme latch: if the prompt contains family markers, latch
        # the family theme for the session so subsequent emotional turns are
        # always shaped (short-circuit relies on this flag).
        prompt_lower_early = prompt.lower()
        if any(m in prompt_lower_early for m in self.EMO_THEME_FAMILY):
            self._family_theme_latched = True
        # Short-circuit: if a family theme has been latched for this session,
        # never call the model for emotional intent — always return a forced
        # emotional skeleton (B or C) deterministically.
        if getattr(self, "_family_theme_latched", False) and intent == "emotional":
            lang_mode = self._emotional_lang_mode(prompt, lang)
            last = self._emo_last_skeleton
            if last == "A" or last is None:
                forced = "B"
            else:
                forced = self._get_next_escalation_skeleton(last)
            if forced == "A":
                forced = "B"
            shaped_text, used = self._render_emotional_skeleton(prompt, lang_mode, forced)
            meta = {
                "source": "escalation_forced",
                "shaped": True,
                "shape": "emotional_escalation",
                "escalation_active": True,
                "emotional_theme": "family",
                "emotional_skeleton": used,
                "emotional_lang": lang_mode,
            }
            return self._pack(shaped_text, meta, return_meta)
        semantic_dropped_reason = None
        best_explanatory = None

        if intent == "factual":
            rule_hit, floor_id = self._factual_floor_answer(prompt, lang)
            if rule_hit:
                cleaned = normalize_output(rule_hit)
                final_text = apply_response_policies(cleaned, intent=intent, lang=lang, prompt=prompt)
                meta = {
                    "source": "factual_floor",
                    "floor_id": floor_id,
                    "floor_verified": (final_text == cleaned),
                }
                final_text, meta = self._post_process_response(
                    prompt, intent, lang, conditioned_prompt, final_text, meta, max_new_tokens
                )
                return self._pack(final_text, meta, return_meta)

        memory_hit = self.memory.lookup(conditioned_prompt)
        if memory_hit:
            cleaned = normalize_output(memory_hit)
            final_text = apply_response_policies(cleaned, intent=intent, lang=lang, prompt=prompt)
            meta = {"source": "memory_exact"}
            if intent != "explanatory":
                final_text, meta = self._post_process_response(
                    prompt, intent, lang, conditioned_prompt, final_text, meta, max_new_tokens
                )
                return self._pack(final_text, meta, return_meta)
            if self._is_good_explanatory_target(final_text):
                final_text, meta = self._post_process_response(
                    prompt, intent, lang, conditioned_prompt, final_text, meta, max_new_tokens
                )
                return self._pack(final_text, meta, return_meta)
            best_explanatory = (final_text, meta)

        # Prefer semantic retrieval for knowledge-heavy intents to reduce unseen prompt drift.
        if intent in {"factual", "explanatory"}:
            if intent == "explanatory":
                semantic_hit = self.memory.lookup_semantic(
                    conditioned_prompt, target_predicate=self._is_good_explanatory_target
                ) or self.memory.lookup_semantic(conditioned_prompt)
            else:
                semantic_hit = self.memory.lookup_semantic(conditioned_prompt)
            if semantic_hit:
                if intent == "explanatory" and not self._is_retrieval_topic_safe(prompt, semantic_hit):
                    semantic_dropped_reason = "topic_mismatch"
                else:
                    cleaned = normalize_output(semantic_hit)
                    final_text = apply_response_policies(cleaned, intent=intent, lang=lang, prompt=prompt)
                    meta = {"source": "memory_semantic"}
                    if intent != "explanatory":
                        final_text, meta = self._post_process_response(
                            prompt, intent, lang, conditioned_prompt, final_text, meta, max_new_tokens
                        )
                        return self._pack(final_text, meta, return_meta)
                    if self._is_good_explanatory_target(final_text):
                        final_text, meta = self._post_process_response(
                            prompt, intent, lang, conditioned_prompt, final_text, meta, max_new_tokens
                        )
                        return self._pack(final_text, meta, return_meta)
                    best_explanatory = (final_text, meta)

        cleaned = self._model_generate_cleaned(conditioned_prompt, max_new_tokens=max_new_tokens)
        final_text = apply_response_policies(cleaned, intent=intent, lang=lang, prompt=prompt)

        # Non-contaminating rescue path for unseen factual/explanatory phrasing:
        # use semantic nearest-neighbor retrieval from existing training data only.
        if intent in {"factual", "explanatory"} and final_text == GENERIC_FALLBACK:
            if intent == "factual":
                rule_hit, floor_id = self._factual_floor_answer(prompt, lang)
                if rule_hit:
                    recovered = normalize_output(rule_hit)
                    recovered_final = apply_response_policies(recovered, intent=intent, lang=lang, prompt=prompt)
                    meta = {
                        "source": "factual_floor",
                        "floor_id": floor_id,
                        "floor_verified": (recovered_final == recovered),
                    }
                    recovered_final, meta = self._post_process_response(
                        prompt, intent, lang, conditioned_prompt, recovered_final, meta, max_new_tokens
                    )
                    return self._pack(recovered_final, meta, return_meta)
            if intent == "explanatory":
                semantic_hit = self.memory.lookup_semantic(
                    conditioned_prompt, target_predicate=self._is_good_explanatory_target
                ) or self.memory.lookup_semantic(conditioned_prompt)
            else:
                semantic_hit = self.memory.lookup_semantic(conditioned_prompt)
            if semantic_hit:
                if intent == "explanatory" and not self._is_retrieval_topic_safe(prompt, semantic_hit):
                    semantic_dropped_reason = "topic_mismatch"
                else:
                    recovered = normalize_output(semantic_hit)
                    recovered_final = apply_response_policies(recovered, intent=intent, lang=lang, prompt=prompt)
                    meta = {"source": "memory_semantic"}
                    recovered_final, meta = self._post_process_response(
                        prompt, intent, lang, conditioned_prompt, recovered_final, meta, max_new_tokens
                    )
                    return self._pack(recovered_final, meta, return_meta)

        meta = {"source": "model"}
        if semantic_dropped_reason:
            meta["semantic_dropped"] = True
            meta["semantic_dropped_reason"] = semantic_dropped_reason
        final_text, meta = self._post_process_response(
            prompt, intent, lang, conditioned_prompt, final_text, meta, max_new_tokens
        )

        # Enforcement: If escalation was signaled or the prompt requires family shaping,
        # ensure the final output is produced from an emotional skeleton (B or C)
        prompt_lower = prompt.lower()
        lang_mode = self._emotional_lang_mode(prompt, lang)
        escalation_flag = bool(
            meta.get("escalation_active")
            or self._emo_escalation_active
            or self._has_resignation_markers(prompt_lower)
        )
        # also trigger escalation if the last two skeletons were the same (repetition signal)
        if len(self._emo_skeleton_history) >= 2 and self._emo_skeleton_history[-1] == self._emo_skeleton_history[-2]:
            escalation_flag = True
        # Family flag now latches for the sequence once detected.
        family_flag = (
            self._family_theme_latched
            or any(m in prompt_lower for m in self.EMO_THEME_FAMILY)
            or (self._emo_theme == "family")
        )

        # Decide whether this turn should be treated as an emotional turn.
        emotional_turn = (
            intent == "emotional"
            or any(m in prompt_lower for m in self.EMO_OVERWHELM_MARKERS)
            or any(m in prompt_lower for m in self.EMO_GUILT_MARKERS)
            or any(m in prompt_lower for m in self.EMO_RESIGNATION_MARKERS)
            or any(m in prompt_lower for m in self.EMO_THEME_PRESSURED)
            or any(m in prompt_lower for m in self.EMO_THEME_FAMILY)
        )

        # Enforce shaping when escalation is active, or when a family theme is latched
        # for the sequence (family enforcement applies to all subsequent turns).
        if (escalation_flag or family_flag):
            # Determine skeleton to force: prefer B if last was A, otherwise advance
            last = self._emo_last_skeleton or meta.get("emotional_skeleton")
            if last == "A" or last is None:
                forced = "B"
            else:
                forced = self._get_next_escalation_skeleton(last)

            # Never allow A-only when enforcing family shaping; coerce to at least B.
            if forced == "A":
                forced = "B"

            shaped_text, used = self._render_emotional_skeleton(prompt, lang_mode, forced)

            # Advice-ban: if shaped text still contains advice-like tokens, switch to C
            lower_shaped = (shaped_text or "").lower()
            if any(b in lower_shaped for b in self.EMO_ADVICE_BAN):
                shaped_text, used = self._render_emotional_skeleton(prompt, lang_mode, "C")

            # Replace final_text/meta with forced-shaped response
            meta = dict(meta)
            meta["source"] = "escalation_forced"
            meta["shaped"] = True
            meta["shape"] = "emotional_escalation"
            meta["escalation_active"] = True
            meta["emotional_skeleton"] = used
            meta["emotional_lang"] = lang_mode
            # If this enforcement is driven by a family latch, expose it explicitly.
            if family_flag:
                meta["emotional_theme"] = "family"
            final_text = shaped_text

        # --- B3.3 Anti-parroting (priority after escalation enforcement) ---
        # Discard responses that strongly echo the user's wording.
        parroting_hit = False
        try:
            parroting_hit = self._is_parroting(prompt, final_text)
        except Exception:
            parroting_hit = False

        if parroting_hit:
            # Re-render using the enforced/next skeleton (avoid raw model output)
            last = self._emo_last_skeleton or meta.get("emotional_skeleton")
            forced = "B" if (last == "A" or last is None) else self._get_next_escalation_skeleton(last)
            final_text, used = self._render_emotional_skeleton(prompt, lang_mode, forced)
            meta = dict(meta)
            meta["source"] = "parroting_block"
            meta["shaped"] = True
            meta["shape"] = "parroting_block"
            meta["emotional_skeleton"] = used

            # If the re-render still looks parroting or contains advice, fall back to C
            if self._is_parroting(prompt, final_text) or any(b in (final_text or "").lower() for b in self.EMO_ADVICE_BAN):
                final_text, used = self._render_emotional_skeleton(prompt, lang_mode, "C")
                meta["shape"] = "emotional_escalation"
                meta["escalation_active"] = True
                meta["emotional_skeleton"] = used

        # --- B3.3 Pushback normalization (after anti-parroting) ---
        if any(m in prompt_lower for m in self.PUSHBACK_MARKERS):
            ack = self._render_pushback_ack(lang)
            final_text = ack
            meta = dict(meta)
            meta["source"] = "pushback_ack"
            meta["shape"] = "pushback_ack"
            meta["shaped"] = True
            meta["emotional_skeleton"] = None

        # If explanatory generation still violates the shape contract, prefer the best memory fallback we saw.
        if intent == "explanatory" and best_explanatory:
            if (not self._is_explanatory_on_topic(prompt, final_text)) or self._needs_explanatory_regen(prompt, final_text):
                best_text, best_meta = best_explanatory
                best_text, best_meta = self._post_process_response(
                    prompt, intent, lang, conditioned_prompt, best_text, best_meta, max_new_tokens
                )
                final_text, meta = best_text, best_meta

        return self._pack(final_text, meta, return_meta)
