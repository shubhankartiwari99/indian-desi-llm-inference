#!/usr/bin/env python3
import sys
import json

ADVICE_KEYWORDS = [
    "should",
    "try to",
    "best way",
    "you need",
    "you should",
    "you've got to",
    "having a healthy",
    "having a healthy life",
    "best thing",
]


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def is_emotional_intent(text):
    # Lightweight heuristic mirroring detect_intent for CI; treat short emotional prompts as emotional.
    if not text:
        return False
    low = text.lower()
    emo_markers = ("feel", "feels", "tired", "anxious", "depressed", "parents", "family", "drained", "overwhelmed", "disappoint")
    return any(m in low for m in emo_markers)


def main(path):
    data = load(path)
    failures = []

    for seq in data.get("sequences", []):
        seq_id = seq.get("id")
        turns = seq.get("turns", [])

        # find first family-latched turn
        latched = None
        for i, t in enumerate(turns):
            meta = t.get("meta", {})
            if meta.get("emotional_theme") == "family":
                latched = i
                break
        if latched is None:
            continue

        # check subsequent emotional turns
        for j in range(latched, len(turns)):
            t = turns[j]
            user = t.get("user", "")
            meta = t.get("meta", {})
            if not is_emotional_intent(user):
                continue

            if meta.get("source") != "escalation_forced":
                failures.append(f"{seq_id}: turn {j+1} not escalation_forced (meta.source={meta.get('source')})")
                continue

            if meta.get("shape") != "emotional_escalation":
                failures.append(f"{seq_id}: turn {j+1} wrong shape {meta.get('shape')}")

            if meta.get("emotional_skeleton") not in {"B", "C"}:
                failures.append(f"{seq_id}: turn {j+1} skeleton {meta.get('emotional_skeleton')}")

            # Future-proof invariant: escalation must never use skeleton A.
            if meta.get("shape") == "emotional_escalation" and meta.get("emotional_skeleton") == "A":
                failures.append(f"{seq_id}: turn {j+1} escalation used skeleton A — forbidden")

            text = t.get("response", "").lower()
            if meta.get("shape") in {"pushback_ack", "emotional_escalation"}:
                for k in ADVICE_KEYWORDS:
                    if k in text:
                        failures.append(f"{seq_id}: turn {j+1} contains advice keyword '{k}'")

    if failures:
        print("CI_VERIFIER_FAILED")
        for f in failures:
            print(f)
        sys.exit(2)
    print("CI_VERIFIER_OK")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: ci_verify_results.py /path/to/results.json")
        sys.exit(1)
    main(sys.argv[1])
