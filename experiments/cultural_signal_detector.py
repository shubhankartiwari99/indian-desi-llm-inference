"""
Cultural Signal Detector — lightweight classifier for Indian cultural alignment.

Scores text on a 0.0–1.0 scale for presence of Indian cultural markers.
Used as the measurement instrument in Experiments 2.1/2.2.

Marker categories:
  1. Lexical: Hindi/Hinglish words, desi expressions
  2. Script: Devanagari character ratio
  3. Contextual: India-specific concepts (IIT, UPI, UPSC, Bollywood, etc.)
  4. Empathy-cultural: culturally-coded emotional language
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


# ─────────────────────────────────────────────────────────────────────────────
# Marker banks
# ─────────────────────────────────────────────────────────────────────────────

# Hindi/Hinglish lexical markers (common desi speech patterns)
HINGLISH_MARKERS = {
    "yaar", "bhai", "arre", "acha", "accha", "theek", "haan",
    "nahi", "bas", "chalo", "kya", "kaise", "kaisa", "kaisi",
    "abhi", "aaj", "kal", "phir", "lekin", "isliye", "kyunki",
    "samajh", "samjh", "dimag", "mann", "dil", "gharwale",
    "pareshaan", "tension", "jugaad", "dhyan", "mehnat",
    "padhai", "parhai", "padh", "seekh", "seekho",
    "sahab", "ji", "sahib", "namaste", "namaskar",
    "bhaiya", "didi", "aunty", "uncle",
    "roti", "chai", "daal", "sabzi", "paratha",
    "baaki", "sab", "thoda", "zyada", "bahut",
    "log", "logon", "pyaar", "mohabbat",
    "zindagi", "duniya", "sapna", "sapne",
}

# India-specific contextual references
INDIA_CONTEXT_MARKERS = {
    "india", "indian", "bharat", "bharatiya", "desi",
    "iit", "nit", "iiit", "iim", "upsc", "jee", "neet",
    "upi", "paytm", "phonepe", "gpay",
    "bollywood", "tollywood", "kollywood",
    "diwali", "deepawali", "holi", "navratri", "durga", "ganesh",
    "eid", "baisakhi", "pongal", "onam", "raksha", "rakshabandhan",
    "guru", "shishya", "parampara", "ashram", "vedic", "vedas",
    "ayurveda", "yoga", "pranayama", "dhyana",
    "caste", "reservation", "obc", "sc", "st", "dalit",
    "mandi", "panchayat", "lok", "sabha", "rajya",
    "rupee", "rupees", "lakh", "crore",
    "sharma", "gupta", "patel", "singh", "khan", "reddy", "kumari",
    "hostel", "mess", "canteen",
    "b.tech", "btech", "m.tech", "mtech", "mbbs",
    "placement", "placements", "campus",
    "joint family", "arranged marriage",
    "rickshaw", "auto-rickshaw", "autorickshaw",
    "mumbai", "delhi", "bangalore", "bengaluru", "chennai",
    "hyderabad", "kolkata", "pune", "jaipur", "lucknow",
    "kerala", "tamil", "telugu", "marathi", "gujarati", "punjabi",
    "hindi", "hinglish", "devanagari",
    "startup ecosystem", "startup culture",
}

# Devanagari Unicode range
DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")
TOKEN_RE = re.compile(r"\w+", re.UNICODE)


# ─────────────────────────────────────────────────────────────────────────────
# Data class
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class CulturalSignal:
    """Result of cultural signal detection on a single text."""
    score: float                              # 0.0 – 1.0
    has_cultural_signal: bool                 # score > threshold
    devanagari_ratio: float                   # fraction of chars that are devanagari
    hinglish_markers_found: list[str] = field(default_factory=list)
    context_markers_found: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "score": round(self.score, 4),
            "has_cultural_signal": self.has_cultural_signal,
            "devanagari_ratio": round(self.devanagari_ratio, 4),
            "hinglish_markers_found": self.hinglish_markers_found,
            "context_markers_found": self.context_markers_found,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Detector
# ─────────────────────────────────────────────────────────────────────────────

def detect_cultural_signal(
    text: str,
    *,
    threshold: float = 0.10,
) -> CulturalSignal:
    """
    Scores text for Indian cultural alignment markers.

    Scoring:
      - Devanagari ratio component:   weight 0.40  (0.0 if none, 1.0 if >20% devanagari)
      - Hinglish marker component:    weight 0.30  (saturates at 3+ markers)
      - Context marker component:     weight 0.30  (saturates at 3+ markers)

    Returns CulturalSignal with score, boolean, and raw marker lists.
    """
    if not text or not text.strip():
        return CulturalSignal(
            score=0.0,
            has_cultural_signal=False,
            devanagari_ratio=0.0,
        )

    lower = text.lower()
    tokens = set(TOKEN_RE.findall(lower))

    # ── 1. Devanagari script ratio ────────────────────────────────────────
    total_chars = len(text.replace(" ", ""))
    dev_chars = len(DEVANAGARI_RE.findall(text))
    devanagari_ratio = dev_chars / max(1, total_chars)

    # Score: 0→0 at 0%, linear to 1.0 at 20%+ devanagari
    dev_score = min(1.0, devanagari_ratio / 0.20)

    # ── 2. Hinglish lexical markers ───────────────────────────────────────
    hinglish_found = sorted(tokens & HINGLISH_MARKERS)
    # Saturate at 3 markers → score = 1.0
    # Even a single marker like "yaar" should cross detection threshold
    hinglish_score = min(1.0, len(hinglish_found) / 3.0)

    # ── 3. India context markers ──────────────────────────────────────────
    # Check both single-token and multi-token markers
    context_found = []
    for marker in INDIA_CONTEXT_MARKERS:
        if " " in marker:
            # Multi-word marker: substring match
            if marker in lower:
                context_found.append(marker)
        else:
            # Single-word marker: token match
            if marker in tokens:
                context_found.append(marker)
    context_found = sorted(set(context_found))
    # Saturate at 3 markers → score = 1.0
    context_score = min(1.0, len(context_found) / 3.0)

    # ── Weighted composite ────────────────────────────────────────────────
    composite = (
        0.40 * dev_score
        + 0.30 * hinglish_score
        + 0.30 * context_score
    )
    composite = round(min(1.0, composite), 4)

    return CulturalSignal(
        score=composite,
        has_cultural_signal=composite >= threshold,
        devanagari_ratio=round(devanagari_ratio, 4),
        hinglish_markers_found=hinglish_found,
        context_markers_found=context_found,
    )


# ─────────────────────────────────────────────────────────────────────────────
# CLI self-test
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_cases = [
        ("Tell me something uplifting.", False),
        ("I feel stuck yaar, what should I do?", True),
        ("मुझे बहुत निराशा महसूस हो रही है।", True),
        ("Explain how UPI payments work.", True),
        ("What is photosynthesis?", False),
        ("IIT ya NIT mein admission ke liye kya strategy best hai?", True),
        ("How does a transistor work?", False),
        ("Explain the importance of Diwali in Indian culture.", True),
        ("The weather is nice today.", False),
        ("Bhai tension mat le, sab theek hoga.", True),
    ]

    print("=" * 70)
    print("CULTURAL SIGNAL DETECTOR — SELF-TEST")
    print("=" * 70)

    passed = 0
    for text, expected in test_cases:
        result = detect_cultural_signal(text)
        match = result.has_cultural_signal == expected
        passed += 1 if match else 0
        status = "✅" if match else "❌"
        print(f"\n{status} \"{text[:60]}...\"" if len(text) > 60 else f"\n{status} \"{text}\"")
        print(f"   Score: {result.score:.3f}  Signal: {result.has_cultural_signal}  Expected: {expected}")
        if result.hinglish_markers_found:
            print(f"   Hinglish: {result.hinglish_markers_found}")
        if result.context_markers_found:
            print(f"   Context:  {result.context_markers_found}")
        if result.devanagari_ratio > 0:
            print(f"   Devanagari: {result.devanagari_ratio:.1%}")

    print(f"\n{'=' * 70}")
    print(f"Results: {passed}/{len(test_cases)} passed")
    print("=" * 70)
