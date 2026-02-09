import json
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Optional, Callable


WS_RE = re.compile(r"\s+", re.UNICODE)
# Keep non-Latin scripts intact (especially Devanagari) and strip mostly ASCII punctuation.
PUNCT_RE = re.compile(r"""[!"#$%&'()*+,\-./:;<=>?@[\\\]^_`{|}~“”‘’…।॥]+""", re.UNICODE)
PREFIX_RE = re.compile(r"^\s*(empathy|fact|explain|uncertain|refusal)\s*:\s*(.*)$", re.IGNORECASE)

STOPWORDS = {
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
    "what",
    "who",
    "when",
    "where",
    "why",
    "how",
    "please",
    "do",
    "does",
    "did",
    "me",
    "my",
    "ka",
    "ki",
    "ke",
    "hai",
    "ho",
    "hota",
    "hoti",
    "kya",
    "kyu",
    "kyon",
    "aur",
    "par",
    "pe",
    "se",
    "ko",
    "mein",
    "abhi",
    "bolo",
    "samjhao",
    "samjha",
    "kaun",
    "tha",
    "kisne",
    "hote",
    "hua",
    "hui",
    "hue",
    "bolo",
    "batao",
    "ab",
    "abhi",
    "sirf",
    "seedha",
    "direct",
    "only",
    "का",
    "की",
    "के",
    "है",
    "हैं",
    "था",
    "थी",
    "थे",
    "कब",
    "क्या",
    "कौन",
    "में",
    "पर",
    "से",
    "को",
    "और",
    "तो",
    "do",
}

TOKEN_CANON = {
    "stands": "stand",
    "standing": "stand",
    "full": "full",
    "form": "form",
    "dns": "dns",
    "http": "http",
    "https": "https",
    "sdk": "sdk",
    "api": "api",
    "currency": "currency",
    "japan": "japan",
    "moon": "moon",
    "chand": "moon",
    "constitution": "constitution",
    "samvidhan": "constitution",
    "संविधान": "constitution",
    "प्रधानमंत्री": "prime_minister",
    "राजधानी": "capital",
    "मुद्रा": "currency",
    "जापान": "japan",
    "चंद्रमा": "moon",
    "चाँद": "moon",
    "कब": "when",
    "लागू": "adopt",
    "हुआ": "adopt",
    "घंटे": "hour",
    "घंटा": "hour",
    "मिनट": "minute",
    "पहला": "first",
    "इंसान": "human",
    "कौन": "who",
    "भारत": "india",
    "india": "india",
    "insaan": "human",
    "human": "human",
    "pehla": "first",
    "first": "first",
    "minutes": "minute",
    "minute": "minute",
    "ghante": "hour",
    "hours": "hour",
    "currency": "currency",
    "yen": "yen",
    "japanese": "japan",
    "apply": "adopt",
    "adopted": "adopt",
    "enforce": "adopt",
    "implemented": "adopt",
    "vector": "vector",
    "database": "database",
    "cache": "cache",
    "overfitting": "overfitting",
    "cricket": "cricket",
    "difference": "difference",
    "fark": "difference",
}


def _normalize(text: str) -> str:
    return WS_RE.sub(" ", text.strip().lower())


def _simplify(text: str) -> str:
    normalized = _normalize(text)
    normalized = normalized.replace("stands for", "full form")
    normalized = normalized.replace("stand for", "full form")
    simplified = PUNCT_RE.sub(" ", normalized)
    return WS_RE.sub(" ", simplified).strip()


def _split_prefixed(text: str):
    match = PREFIX_RE.match(text.strip())
    if not match:
        return None, text.strip()
    return match.group(1).lower(), match.group(2).strip()


def _normalized_tokens(text: str):
    toks = []
    for token in _simplify(text).split():
        canon = TOKEN_CANON.get(token, token)
        if canon.isdigit():
            toks.append(canon)
            continue
        if canon in STOPWORDS:
            continue
        toks.append(canon)
    return toks


class AlignmentMemory:
    def __init__(self, data_path: str = "data/alignment_gold_mt5_expanded.jsonl"):
        self.by_normalized = {}
        self.by_simplified = {}
        self.by_prefix = {"fact": [], "explain": []}
        self._seen_prefix_inputs = set()

        path = Path(data_path)
        if not path.exists():
            return

        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue

                input_text = str(obj.get("input_text", "")).strip()
                target_text = str(obj.get("target_text", "")).strip()
                if not input_text or not target_text:
                    continue

                nkey = _normalize(input_text)
                skey = _simplify(input_text)

                if nkey not in self.by_normalized:
                    self.by_normalized[nkey] = target_text
                if skey and skey not in self.by_simplified:
                    self.by_simplified[skey] = target_text

                prefix, body = _split_prefixed(input_text)
                if prefix in self.by_prefix:
                    body_simplified = _simplify(body)
                    if not body_simplified:
                        continue
                    dedupe_key = (prefix, body_simplified)
                    if dedupe_key in self._seen_prefix_inputs:
                        continue
                    self._seen_prefix_inputs.add(dedupe_key)
                    self.by_prefix[prefix].append(
                        {
                            "body": body,
                            "body_simplified": body_simplified,
                            "tokens": set(_normalized_tokens(body)),
                            "target": target_text,
                        }
                    )

    def lookup(self, conditioned_prompt: str) -> Optional[str]:
        nkey = _normalize(conditioned_prompt)
        hit = self.by_normalized.get(nkey)
        if hit:
            return hit

        skey = _simplify(conditioned_prompt)
        if not skey:
            return None

        return self.by_simplified.get(skey)

    def lookup_semantic(
        self,
        conditioned_prompt: str,
        min_score: float = 0.48,
        target_predicate: Optional[Callable[[str], bool]] = None,
    ) -> Optional[str]:
        prefix, body = _split_prefixed(conditioned_prompt)
        if prefix not in self.by_prefix:
            return None

        query_simplified = _simplify(body)
        query_tokens = set(_normalized_tokens(body))
        if not query_simplified:
            return None

        best = None
        best_score = 0.0

        for candidate in self.by_prefix[prefix]:
            if target_predicate and (not target_predicate(candidate["target"])):
                continue
            cand_tokens = candidate["tokens"]
            shared = query_tokens & cand_tokens
            if not shared:
                continue

            # Avoid weak single-token collisions unless it looks like an acronym/number key token.
            if len(shared) == 1:
                only = next(iter(shared))
                if not (len(only) <= 4 or any(ch.isdigit() for ch in only)):
                    continue

            token_score = len(shared) / max(1, min(len(query_tokens), len(cand_tokens)))
            seq_score = SequenceMatcher(None, query_simplified, candidate["body_simplified"]).ratio()
            score = max(token_score, seq_score)

            if score > best_score:
                best_score = score
                best = candidate["target"]

        if best and best_score >= min_score:
            return best
        return None
