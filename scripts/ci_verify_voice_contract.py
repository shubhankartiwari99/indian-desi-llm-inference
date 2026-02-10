#!/usr/bin/env python3
import json
import re
import sys
from typing import Dict, List, Tuple

from app.intent import detect_intent


ADVICE_KEYWORDS = [
    "should",
    "try",
    "try to",
    "best way",
    "you need",
    "you should",
    "you've got to",
    "having a healthy",
    "having a healthy life",
    "best thing",
]

HINGLISH_MARKERS = (
    "yeh",
    "ye",
    "kaafi",
    "zyada",
    "lag",
    "raha",
    "hoga",
    "aisa",
    "iska",
    "matlab",
    "zaroori",
    "nahi",
    "abhi",
    "chaho",
    "thoda",
    "bata",
    "samajh",
    "dheere",
    "kaise",
    "kyun",
    "kya",
    "aap",
    "ho",
    "hai",
    "mein",
    "moment",
)

RESIGNATION_MARKERS = (
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
)

TIMEBOX_PATTERNS = [
    re.compile(r"\b(\d{1,2})\s*[- ]?\s*(min|mins|minute|minutes)\b"),
    re.compile(r"\btonight\b"),
    re.compile(r"\bthis\s+evening\b"),
    re.compile(r"\bright\s+now\b"),
    re.compile(r"\btoday\b"),
    re.compile(r"\baaj\b"),
    re.compile(r"\babhi\b"),
]

ACTION_REQUEST_MARKERS = (
    "reset",
    "cope",
    "deal",
    "handle",
    "manage",
    "get through",
    "calm down",
    "calm",
    "ground",
    "focus",
    "practical step",
    "small step",
    "kya karun",
    "what should i do",
)

LATIN_ACTION_MARKERS = (
    "breathe",
    "breathing",
    "inhale",
    "exhale",
    "set a",
    "timer",
    "count",
    "step",
    "do ",
    "try ",
)


def load_json(path: str):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def normalize_text(text: str) -> str:
    return " ".join(text.strip().split())


def detect_lang_mode(response: str) -> str:
    if re.search(r"[\u0900-\u097F]", response):
        return "hi"
    lower = response.lower()
    if any(m in lower for m in HINGLISH_MARKERS):
        return "hinglish"
    return "en"


def load_contract(md_path: str) -> Dict[str, Dict[str, Dict[str, List[str]]]]:
    contract: Dict[str, Dict[str, Dict[str, List[str]]]] = {}
    current_skeleton = None
    current_lang = None
    current_section = None

    with open(md_path, encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line:
                continue

            sk_match = re.match(r"^##\s+Skeleton\s+([A-D])\b", line)
            if sk_match:
                current_skeleton = sk_match.group(1)
                contract.setdefault(current_skeleton, {})
                current_lang = None
                current_section = None
                continue

            if line == "English (en)":
                current_lang = "en"
            elif line == "Hinglish":
                current_lang = "hinglish"
            elif line == "Hindi (hi)":
                current_lang = "hi"

            if current_lang and current_skeleton:
                contract[current_skeleton].setdefault(current_lang, {})

            if line.startswith("- Opener"):
                current_section = "opener"
            elif line.startswith("- Validation"):
                current_section = "validation"
            elif line.startswith("- Closure"):
                current_section = "closure"
            elif line.startswith("- Action"):
                current_section = "action"

            if line.startswith("-"):
                match = re.search(r'"([^"]+)"', line)
                if match and current_skeleton and current_lang and current_section:
                    contract[current_skeleton][current_lang].setdefault(current_section, [])
                    contract[current_skeleton][current_lang][current_section].append(match.group(1))

    return contract


def is_timeboxed_request(prompt: str) -> bool:
    lower = prompt.lower()
    has_time = any(p.search(lower) for p in TIMEBOX_PATTERNS)
    has_action = any(marker in lower for marker in ACTION_REQUEST_MARKERS)
    return has_time and has_action


def has_resignation_markers(prompt: str) -> bool:
    lower = prompt.lower()
    return any(m in lower for m in RESIGNATION_MARKERS)


def iter_turns(data) -> List[Tuple[str, int, str, str, dict]]:
    if isinstance(data, dict) and "sequences" in data:
        turns_out = []
        for seq in data.get("sequences", []):
            seq_id = seq.get("id", "unknown_seq")
            turns = seq.get("turns", [])
            for idx, t in enumerate(turns, start=1):
                turns_out.append(
                    (
                        str(seq_id),
                        t.get("turn_index") or idx,
                        t.get("user", ""),
                        t.get("response", ""),
                        t.get("meta", {}) or {},
                    )
                )
        return turns_out

    if isinstance(data, list):
        turns_out = []
        for idx, item in enumerate(data, start=1):
            turns_out.append(
                (
                    f"item{idx}",
                    1,
                    item.get("prompt", ""),
                    item.get("response", ""),
                    item.get("meta", {}) or {},
                )
            )
        return turns_out

    return []


def build_allowed_responses(contract: Dict[str, Dict[str, Dict[str, List[str]]]]) -> Dict[Tuple[str, str], List[str]]:
    allowed: Dict[Tuple[str, str], List[str]] = {}
    for skeleton, langs in contract.items():
        for lang, sections in langs.items():
            opener = sections.get("opener", [])
            validation = sections.get("validation", [])
            closure = sections.get("closure", [])
            action = sections.get("action", [])

            combos = []
            if skeleton == "D":
                for o in opener:
                    for a in action:
                        for c in closure:
                            combos.append(normalize_text(f"{o} {a} {c}"))
            else:
                for o in opener:
                    for v in validation:
                        for c in closure:
                            combos.append(normalize_text(f"{o} {v} {c}"))

            allowed[(skeleton, lang)] = combos
    return allowed


def contract_action_phrases(contract: Dict[str, Dict[str, Dict[str, List[str]]]]) -> List[str]:
    actions = []
    for lang, sections in contract.get("D", {}).items():
        actions.extend(sections.get("action", []))
    return actions


def check_language_purity(seq_id: str, turn_idx: int, lang_mode: str, response: str, failures: List[str]):
    has_dev = bool(re.search(r"[\u0900-\u097F]", response))
    has_latin = bool(re.search(r"[A-Za-z]", response))
    lower = response.lower()

    if lang_mode == "hi":
        if not has_dev or has_latin:
            failures.append(f"{seq_id}: turn {turn_idx} hindi purity violation")
    elif lang_mode == "hinglish":
        if has_dev:
            failures.append(f"{seq_id}: turn {turn_idx} hinglish contains devanagari")
        if not any(m in lower for m in HINGLISH_MARKERS):
            failures.append(f"{seq_id}: turn {turn_idx} hinglish missing markers")
    elif lang_mode == "en":
        if has_dev:
            failures.append(f"{seq_id}: turn {turn_idx} english contains devanagari")


def check_turn(
    seq_id: str,
    turn_idx: int,
    user: str,
    response: str,
    meta: dict,
    contract: Dict[str, Dict[str, Dict[str, List[str]]]],
    allowed: Dict[Tuple[str, str], List[str]],
    action_phrases: List[str],
    failures: List[str],
):
    if not response:
        return

    intent = detect_intent(user) if user else None
    skeleton = meta.get("emotional_skeleton")
    shape = meta.get("shape")
    theme = meta.get("emotional_theme")

    if intent == "emotional" and not skeleton:
        failures.append(f"{seq_id}: turn {turn_idx} missing emotional_skeleton meta")
        return

    if not skeleton:
        return

    if skeleton not in {"A", "B", "C", "D"}:
        failures.append(f"{seq_id}: turn {turn_idx} unknown skeleton {skeleton}")
        return

    if shape == "emotional_escalation" and skeleton not in {"B", "C"}:
        failures.append(f"{seq_id}: turn {turn_idx} escalation used skeleton {skeleton}")

    if theme == "family" and skeleton not in {"B", "C"}:
        failures.append(f"{seq_id}: turn {turn_idx} family theme used skeleton {skeleton}")

    if has_resignation_markers(user) and skeleton != "C":
        failures.append(f"{seq_id}: turn {turn_idx} resignation requires skeleton C")

    if intent == "emotional" and is_timeboxed_request(user) and skeleton != "D":
        failures.append(f"{seq_id}: turn {turn_idx} time-boxed request requires skeleton D")

    text_lower = response.lower()
    if skeleton in {"A", "B", "C"}:
        for kw in ADVICE_KEYWORDS:
            if kw in text_lower:
                failures.append(f"{seq_id}: turn {turn_idx} contains advice keyword '{kw}'")
                break

    if skeleton == "C":
        if any(a.lower() in text_lower for a in action_phrases):
            failures.append(f"{seq_id}: turn {turn_idx} skeleton C contains action phrasing")
        if any(m in text_lower for m in LATIN_ACTION_MARKERS):
            failures.append(f"{seq_id}: turn {turn_idx} skeleton C contains action verbs")

    lang_mode = meta.get("emotional_lang") or detect_lang_mode(response)
    check_language_purity(seq_id, turn_idx, lang_mode, response, failures)

    allowed_responses = allowed.get((skeleton, lang_mode), [])
    normalized = normalize_text(response)
    if normalized not in allowed_responses:
        failures.append(f"{seq_id}: turn {turn_idx} response not in allowed table for {skeleton}/{lang_mode}")


def main(md_path: str, results_path: str):
    contract = load_contract(md_path)
    allowed = build_allowed_responses(contract)
    action_phrases = contract_action_phrases(contract)

    data = load_json(results_path)
    failures: List[str] = []

    for seq_id, turn_idx, user, response, meta in iter_turns(data):
        check_turn(seq_id, turn_idx, user, response, meta, contract, allowed, action_phrases, failures)

    if failures:
        print("CI_VOICE_CONTRACT_FAILED")
        for f in failures:
            print(f)
        sys.exit(2)

    print("CI_VOICE_CONTRACT_OK")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: ci_verify_voice_contract.py /path/to/contract.md /path/to/results.json")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
