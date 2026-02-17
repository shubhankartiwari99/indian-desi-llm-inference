import os
import json
import copy
import torch
import re
from typing import Optional
from app.model_loader import ModelLoader
from app.intent import detect_intent
from app.language import detect_language
from app.policies import apply_response_policies, GENERIC_FALLBACK, REFUSAL_FALLBACK
from app.utils import normalize_output
from app.alignment_memory import AlignmentMemory
from app.voice.state import SessionVoiceState
from app.voice.rotation_memory import RotationMemory
from app.voice.runtime import (
    EmotionalSignals,
    resolve_emotional_skeleton,
    update_session_state,
)
from app.voice.select import select_voice_variants
from app.voice.assembler import assemble_response
from app.voice.errors import (
    VoiceAssemblyError,
    VoiceContractError,
    VoiceSelectionError,
    VoiceStateError,
)
from app.voice.fallbacks import (
    ABSOLUTE_FALLBACK,
    SKELETON_SAFE_EN_FALLBACK,
    build_skeleton_local_fallback,
    sections_for_skeleton,
)


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
        "just how life is now",
        "how life is now",
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
    def _emotional_lang_mode(cls, prompt: str, lang: str) -> str:
        if lang == "hi":
            return "hi"
        prompt_lower = prompt.lower()
        if cls._prompt_looks_hinglish(prompt_lower):
            return "hinglish"
        return "en"

    def _build_emotional_signals(self, prompt: str, lang: str) -> EmotionalSignals:
        prompt_lower = prompt.lower()
        return EmotionalSignals(
            lang_mode=self._emotional_lang_mode(prompt, lang),
            wants_action=self._needs_emotional_action_shaping(prompt_lower),
            has_overwhelm=(
                any(m in prompt_lower for m in self.EMO_OVERWHELM_MARKERS)
                or any(m in prompt_lower for m in self.EMO_THEME_PRESSURED)
            ),
            has_guilt=any(m in prompt_lower for m in self.EMO_GUILT_MARKERS),
            has_resignation=self._has_resignation_markers(prompt_lower),
            theme=self._detect_emotional_theme(prompt_lower),
            family_theme=any(m in prompt_lower for m in self.EMO_THEME_FAMILY),
        )

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
    def _has_resignation_markers(cls, prompt_lower: str) -> bool:
        """
        Detect if the user is expressing resignation, futility, or stuckness.
        B3.2 escalation trigger condition B.
        """
        return any(m in prompt_lower for m in cls.EMO_RESIGNATION_MARKERS)

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
        resolution=None,
    ):
        """
        Deterministic shaping + micro quality checks.
        This runs after intent detection and after (optional) memory retrieval.
        """
        if not text:
            return text, meta

        # Step 1: Emotional selection/assembly (Phase 3A).
        if intent == "emotional":
            # Never override a safety refusal that was enforced by policies.
            if text.strip() == REFUSAL_FALLBACK:
                return text, meta

            fallback_lang = lang if lang in {"en", "hinglish", "hi"} else "en"
            try:
                if resolution is None:
                    fallback_signals = self._build_emotional_signals(prompt, lang)
                    resolution = resolve_emotional_skeleton(
                        intent=intent,
                        state=self.voice_state,
                        signals=fallback_signals,
                    )

                skeleton = resolution.emotional_skeleton or "A"
                emotional_lang = resolution.emotional_lang if resolution.emotional_lang in {"en", "hinglish", "hi"} else fallback_lang
                selected = select_voice_variants(
                    session_state=self.voice_state,
                    skeleton=skeleton,
                    language=emotional_lang,
                )
                shaped_text = assemble_response(skeleton, selected)

                meta = dict(meta)
                if os.environ.get("RUNTIME_DIAGNOSTICS") == "1":
                    meta["shaped"] = True
                    meta["shape"] = "emotional_escalation" if (resolution and resolution.escalation_state != "none") else "emotional_skeleton"
                meta["emotional_skeleton"] = skeleton
                meta["emotional_lang"] = emotional_lang
                meta["escalation_state"] = self.voice_state.escalation_state
                meta["latched_theme"] = self.voice_state.latched_theme
                meta["emotional_turn_index"] = self.voice_state.emotional_turn_index

                if self.voice_state.escalation_state != "none":
                    if os.environ.get("RUNTIME_DIAGNOSTICS") == "1":
                        meta["escalation_active"] = True
                if self.voice_state.latched_theme:
                    if os.environ.get("RUNTIME_DIAGNOSTICS") == "1":
                        meta["emotional_theme"] = self.voice_state.latched_theme

                return shaped_text, meta

            except VoiceContractError as exc:
                fallback_skeleton = (resolution.emotional_skeleton or "A") if resolution else "A"
                return self._absolute_voice_fallback(fallback_skeleton, fallback_lang, error=exc, stage="contract")
            except VoiceSelectionError as exc:
                skeleton = (resolution.emotional_skeleton or "A") if resolution else "A"
                emotional_lang = (resolution.emotional_lang or fallback_lang) if resolution else fallback_lang
                return self._emotional_fallback_hierarchy(
                    skeleton=skeleton,
                    language=emotional_lang,
                    error=exc,
                    stage="selection",
                    start_level=1,
                )
            except VoiceStateError as exc:
                skeleton = (resolution.emotional_skeleton or "A") if resolution else "A"
                emotional_lang = (resolution.emotional_lang or fallback_lang) if resolution else fallback_lang
                return self._emotional_fallback_hierarchy(
                    skeleton=skeleton,
                    language=emotional_lang,
                    error=exc,
                    stage="state",
                    start_level=2,
                )
            except VoiceAssemblyError as exc:
                skeleton = (resolution.emotional_skeleton or "A") if resolution else "A"
                emotional_lang = (resolution.emotional_lang or fallback_lang) if resolution else fallback_lang
                return self._emotional_fallback_hierarchy(
                    skeleton=skeleton,
                    language=emotional_lang,
                    error=exc,
                    stage="assembly",
                    start_level=1,
                )

        # Step 2 + Step 3: explanatory shaping + topic micro-check + contract-driven regen.
        if intent == "explanatory":
            shaped = self._shape_explanatory(prompt, text)
            if shaped != text:
                meta = dict(meta)
                if os.environ.get("RUNTIME_DIAGNOSTICS") == "1":
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
                    if os.environ.get("RUNTIME_DIAGNOSTICS") == "1":
                        meta["post_regen"] = True
                        meta["post_regen_prompt"] = "shape_contract"
                    return regenerated_final, meta

            return text, meta

        # Default: no shaping.
        return text, meta

    def __init__(self, model_dir: str):
        loader = ModelLoader(model_dir)
        self.model, self.tokenizer = loader.load()
        self.memory = AlignmentMemory()

        self.device = next(self.model.parameters()).device

        self.model.config.decoder_start_token_id = self.tokenizer.pad_token_id
        self.bad_words_ids = self._build_sentinel_blocklist()
        self.model.eval()

        self.voice_state = SessionVoiceState(
            rotation_memory=RotationMemory()
        )
        self._voice_state_turn_snapshot = None
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

    def _restore_voice_state_snapshot(self):
        if self._voice_state_turn_snapshot is not None:
            self.voice_state = copy.deepcopy(self._voice_state_turn_snapshot)

    def _record_emotional_fallback_usage(self, skeleton: str, language: str, variant_id: int):
        if not hasattr(self.voice_state, "rotation_memory") or self.voice_state.rotation_memory is None:
            raise VoiceStateError("rotation_memory unavailable during fallback update")
        turn_index = int(self.voice_state.emotional_turn_index or 0)
        for section in sections_for_skeleton(skeleton):
            pool_key = (skeleton, language, section)
            try:
                self.voice_state.rotation_memory.record_usage(pool_key, int(variant_id), turn_index)
            except (TypeError, AttributeError, KeyError, ValueError) as exc:
                raise VoiceStateError(f"Failed fallback rotation update for {pool_key}") from exc

    def _voice_fallback_meta(
        self,
        *,
        skeleton: str,
        language: str,
        level: int,
        error: Exception,
        stage: str,
        source: str,
    ) -> dict:
        return {
            "source": source,
            "shaped": True,
            "shape": "emotional_fallback",
            "voice_fallback_level": level,
            "voice_fallback_stage": stage,
            "voice_error_class": error.__class__.__name__,
            "emotional_skeleton": skeleton,
            "emotional_lang": language,
            "escalation_state": self.voice_state.escalation_state,
            "latched_theme": self.voice_state.latched_theme,
            "emotional_turn_index": self.voice_state.emotional_turn_index,
        }

    def _absolute_voice_fallback(self, skeleton: str, language: str, error: Exception, stage: str):
        fallback_skeleton = skeleton if skeleton in ABSOLUTE_FALLBACK else "A"
        self._restore_voice_state_snapshot()
        meta = self._voice_fallback_meta(
            skeleton=fallback_skeleton,
            language=(language if language in {"en", "hinglish", "hi"} else "en"),
            level=3,
            error=error,
            stage=stage,
            source="voice_fallback_absolute",
        )
        meta["voice_fallback_type"] = "absolute"
        meta["absolute_fallback"] = True
        return ABSOLUTE_FALLBACK[fallback_skeleton], meta

    def _skeleton_local_voice_fallback(self, skeleton: str, language: str, error: Exception, stage: str):
        text = build_skeleton_local_fallback(skeleton, language)
        self._record_emotional_fallback_usage(skeleton, language, variant_id=0)
        meta = self._voice_fallback_meta(
            skeleton=skeleton,
            language=language,
            level=1,
            error=error,
            stage=stage,
            source="voice_fallback_local",
        )
        meta["voice_fallback_type"] = "skeleton_local"
        return text, meta

    def _skeleton_safe_en_voice_fallback(self, skeleton: str, error: Exception, stage: str):
        fallback_skeleton = skeleton if skeleton in SKELETON_SAFE_EN_FALLBACK else "A"
        text = SKELETON_SAFE_EN_FALLBACK[fallback_skeleton]
        self._record_emotional_fallback_usage(fallback_skeleton, "en", variant_id=-1)
        meta = self._voice_fallback_meta(
            skeleton=fallback_skeleton,
            language="en",
            level=2,
            error=error,
            stage=stage,
            source="voice_fallback_safe_en",
        )
        meta["voice_fallback_type"] = "skeleton_safe_en"
        return text, meta

    def _emotional_fallback_hierarchy(
        self,
        *,
        skeleton: str,
        language: str,
        error: Exception,
        stage: str,
        start_level: int,
    ):
        if start_level <= 1:
            try:
                return self._skeleton_local_voice_fallback(skeleton, language, error=error, stage=stage)
            except (VoiceContractError, VoiceAssemblyError, VoiceStateError) as fallback_exc:
                error = fallback_exc
                stage = "fallback_local"

        if start_level <= 2:
            try:
                return self._skeleton_safe_en_voice_fallback(skeleton, error=error, stage=stage)
            except VoiceStateError as fallback_exc:
                error = fallback_exc
                stage = "fallback_safe_en"

        return self._absolute_voice_fallback(skeleton, language, error=error, stage=stage)

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

    def handle_user_input(self, text: str):
        intent = detect_intent(text)
        lang = detect_language(text)
        conditioned_prompt = self._prepare_prompt(text)
        emotional_signals = self._build_emotional_signals(text, lang)
        emotional_resolution = resolve_emotional_skeleton(
            intent=intent,
            state=self.voice_state,
            signals=emotional_signals,
        )
        update_session_state(
            state=self.voice_state,
            intent=intent,
            resolution=emotional_resolution,
        )
        return intent, lang, conditioned_prompt, emotional_resolution

    @torch.no_grad()
    def generate(self, prompt: str, max_new_tokens: int = 64, return_meta: bool = False):
        self._voice_state_turn_snapshot = copy.deepcopy(self.voice_state)
        try:
            intent, lang, conditioned_prompt, emotional_resolution = self.handle_user_input(prompt)
        except VoiceStateError as exc:
            intent = detect_intent(prompt)
            lang = detect_language(prompt)
            if intent == "emotional":
                text, meta = self._absolute_voice_fallback("A", lang, error=exc, stage="state_update")
                return self._pack(text, meta, return_meta)
            raise
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
                    prompt, intent, lang, conditioned_prompt, final_text, meta, max_new_tokens, emotional_resolution
                )
                return self._pack(final_text, meta, return_meta)

        memory_hit = self.memory.lookup(conditioned_prompt)
        if memory_hit:
            cleaned = normalize_output(memory_hit)
            final_text = apply_response_policies(cleaned, intent=intent, lang=lang, prompt=prompt)
            meta = {"source": "memory_exact"}
            if intent != "explanatory":
                final_text, meta = self._post_process_response(
                    prompt, intent, lang, conditioned_prompt, final_text, meta, max_new_tokens, emotional_resolution
                )
                return self._pack(final_text, meta, return_meta)
            if self._is_good_explanatory_target(final_text):
                final_text, meta = self._post_process_response(
                    prompt, intent, lang, conditioned_prompt, final_text, meta, max_new_tokens, emotional_resolution
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
                            prompt, intent, lang, conditioned_prompt, final_text, meta, max_new_tokens, emotional_resolution
                        )
                        return self._pack(final_text, meta, return_meta)
                    if self._is_good_explanatory_target(final_text):
                        final_text, meta = self._post_process_response(
                            prompt, intent, lang, conditioned_prompt, final_text, meta, max_new_tokens, emotional_resolution
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
                        prompt, intent, lang, conditioned_prompt, recovered_final, meta, max_new_tokens, emotional_resolution
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
                        prompt, intent, lang, conditioned_prompt, recovered_final, meta, max_new_tokens, emotional_resolution
                    )
                    return self._pack(recovered_final, meta, return_meta)

        meta = {}
        if os.environ.get("RUNTIME_DIAGNOSTICS") == "1":
            meta["source"] = "model"
        if semantic_dropped_reason:
            if os.environ.get("RUNTIME_DIAGNOSTICS") == "1":
                meta["semantic_dropped"] = True
                meta["semantic_dropped_reason"] = semantic_dropped_reason
        final_text, meta = self._post_process_response(
            prompt, intent, lang, conditioned_prompt, final_text, meta, max_new_tokens, emotional_resolution
        )
        if intent == "emotional":
            return self._pack(final_text, meta, return_meta)

        # If explanatory generation still violates the shape contract, prefer the best memory fallback we saw.
        if intent == "explanatory" and best_explanatory:
            if (not self._is_explanatory_on_topic(prompt, final_text)) or self._needs_explanatory_regen(prompt, final_text):
                best_text, best_meta = best_explanatory
                best_text, best_meta = self._post_process_response(
                    prompt, intent, lang, conditioned_prompt, best_text, best_meta, max_new_tokens, emotional_resolution
                )
                final_text, meta = best_text, best_meta

        meta = dict(meta)
        if intent == "emotional":
            meta["emotional_skeleton"] = emotional_resolution.emotional_skeleton
            meta["emotional_lang"] = emotional_resolution.emotional_lang
            meta["escalation_state"] = self.voice_state.escalation_state
            meta["latched_theme"] = self.voice_state.latched_theme
            meta["emotional_turn_index"] = self.voice_state.emotional_turn_index
            if self.voice_state.escalation_state != "none":
                meta["shape"] = "emotional_escalation"
                meta["escalation_active"] = True
        else:
            meta["emotional_skeleton"] = None

        return self._pack(final_text, meta, return_meta)

_engine = None

def get_engine():
    global _engine
    if _engine is None:
        model_dir = os.environ.get("MODEL_DIR")
        if not model_dir:
            raise ValueError("MODEL_DIR environment variable must be set to initialize engine.")
        _engine = InferenceEngine(model_dir)
    return _engine

def inference(user_input: str, session_id: str) -> str:
    engine = get_engine()
    # a simple wrapper around the generate method
    response, meta = engine.generate(user_input, return_meta=True)
    return json.dumps({"response": response, "meta": meta})
