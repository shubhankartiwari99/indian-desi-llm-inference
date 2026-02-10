#!/usr/bin/env python3
import json
import re
import sys
from collections import Counter, defaultdict
from typing import Dict, List, Tuple


WINDOW_SIZE = 50
OPENER_CONCENTRATION_WARN = 0.65

EMOTION_WORDS = (
    "heavy",
    "tired",
    "overwhelmed",
    "drained",
    "exhausting",
    "pressure",
    "burden",
    "anxious",
    "panic",
    "lonely",
)

RELATIONAL_WORDS = (
    "carry",
    "hold",
    "with you",
    "here",
    "stay",
    "together",
)


def load_json(path: str):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def normalize(text: str) -> str:
    return " ".join(text.strip().split())


def iter_emotional_turns(data) -> List[Tuple[str, int, str, str, dict]]:
    turns = []
    if isinstance(data, dict) and "sequences" in data:
        for seq in data.get("sequences", []):
            seq_id = str(seq.get("id", "unknown_seq"))
            for idx, t in enumerate(seq.get("turns", []), start=1):
                meta = t.get("meta", {}) or {}
                if meta.get("emotional_skeleton"):
                    turns.append((seq_id, idx, t.get("user", ""), t.get("response", ""), meta))
    elif isinstance(data, list):
        for idx, item in enumerate(data, start=1):
            meta = item.get("meta", {}) or {}
            if meta.get("emotional_skeleton"):
                turns.append((f"item{idx}", 1, item.get("prompt", ""), item.get("response", ""), meta))
    return turns


def split_sentences(text: str) -> List[str]:
    if not text:
        return []
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]


def extract_opener(response: str) -> str:
    parts = split_sentences(response)
    return normalize(parts[0]) if parts else ""


def emotional_lexical_density(text: str) -> float:
    lower = text.lower()
    tokens = re.findall(r"[a-z']+", lower)
    if not tokens:
        return 0.0
    hits = sum(1 for t in tokens if t in EMOTION_WORDS) + sum(
        1 for phrase in RELATIONAL_WORDS if phrase in lower
    )
    return hits / max(len(tokens), 1)


def structure_signature(response: str) -> str:
    parts = split_sentences(response)
    return "|".join("short" if len(p.split()) <= 6 else "long" for p in parts)


def report_opener_concentration(grouped: Dict[Tuple[str, str], List[str]]) -> List[str]:
    warnings = []
    for key, openers in grouped.items():
        window = openers[-WINDOW_SIZE:]
        if not window:
            continue
        counts = Counter(window)
        top_opener, top_count = counts.most_common(1)[0]
        ratio = top_count / len(window)
        if ratio > OPENER_CONCENTRATION_WARN:
            sk, lang = key
            warnings.append(
                f"VOICE_DRIFT_WARNING opener_concentration {sk}/{lang} {ratio:.2f} top='{top_opener}'"
            )
    return warnings


def report_validation_diversity(grouped: Dict[Tuple[str, str], List[str]]) -> List[str]:
    warnings = []
    for key, validations in grouped.items():
        window = validations[-WINDOW_SIZE:]
        unique = len(set(window))
        if window and unique <= 1:
            sk, lang = key
            warnings.append(f"VOICE_DRIFT_WARNING validation_diversity {sk}/{lang} unique={unique}")
    return warnings


def report_flattening(trend: Dict[Tuple[str, str], List[float]]) -> List[str]:
    warnings = []
    for key, densities in trend.items():
        window = densities[-WINDOW_SIZE:]
        if len(window) < 6:
            continue
        first = sum(window[:3]) / 3.0
        last = sum(window[-3:]) / 3.0
        if last < first * 0.6:
            sk, lang = key
            warnings.append(
                f"VOICE_DRIFT_WARNING emotional_flattening {sk}/{lang} first={first:.3f} last={last:.3f}"
            )
    return warnings


def report_structure_repetition(grouped: Dict[Tuple[str, str], List[str]]) -> List[str]:
    warnings = []
    for key, signatures in grouped.items():
        window = signatures[-WINDOW_SIZE:]
        if not window:
            continue
        counts = Counter(window)
        top_sig, top_count = counts.most_common(1)[0]
        if top_count / len(window) > 0.7:
            sk, lang = key
            warnings.append(
                f"VOICE_DRIFT_WARNING structure_repetition {sk}/{lang} {top_count}/{len(window)} sig='{top_sig}'"
            )
    return warnings


def main(results_path: str):
    data = load_json(results_path)
    turns = iter_emotional_turns(data)

    opener_by = defaultdict(list)
    validation_by = defaultdict(list)
    density_by = defaultdict(list)
    structure_by = defaultdict(list)

    for _, _, _, response, meta in turns:
        skeleton = meta.get("emotional_skeleton")
        lang = meta.get("emotional_lang", "en")
        key = (skeleton, lang)
        response_norm = normalize(response)
        sentences = split_sentences(response_norm)

        if sentences:
            opener_by[key].append(sentences[0])
        if len(sentences) > 1:
            validation_by[key].append(sentences[1])
        density_by[key].append(emotional_lexical_density(response_norm))
        structure_by[key].append(structure_signature(response_norm))

    warnings = []
    warnings.extend(report_opener_concentration(opener_by))
    warnings.extend(report_validation_diversity(validation_by))
    warnings.extend(report_flattening(density_by))
    warnings.extend(report_structure_repetition(structure_by))

    if warnings:
        print("VOICE_DRIFT_WARNINGS")
        for w in warnings:
            print(w)
    else:
        print("VOICE_DRIFT_OK")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: ci_voice_drift_report.py /path/to/results.json")
        sys.exit(1)
    main(sys.argv[1])
