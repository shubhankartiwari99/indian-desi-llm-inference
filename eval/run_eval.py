if __name__ == "__main__" and __package__ is None:
    from pathlib import Path
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[1]))

import argparse
import json
from app.inference import InferenceEngine

EXPECTED = {
    "emotional": "empathetic",
    "factual": "direct_fact",
    "explanatory": "clear_explanation",
    "uncertain": "safe_uncertainty",
    "refusal": "safe_refusal"
}

CATEGORY_ALIASES = {
    "emotional": "emotional",
    "factual": "factual",
    "fact": "factual",
    "explanatory": "explanatory",
    "explain": "explanatory",
    "uncertain": "uncertain",
    "refusal": "refusal",
}


def parse_args():
    parser = argparse.ArgumentParser(description="Run offline eval prompts against inference.")
    parser.add_argument("--model-dir", default="artifacts/alignment_lora/final")
    parser.add_argument("--prompts-file", default="eval/prompts_full.json")
    parser.add_argument("--output-file", default="eval/results_9d.json")
    parser.add_argument("--max-new-tokens", type=int, default=128)
    return parser.parse_args()


def normalize_category(raw):
    return CATEGORY_ALIASES.get(str(raw).strip().lower())


def main():
    args = parse_args()
    engine = InferenceEngine(args.model_dir)

    with open(args.prompts_file, encoding="utf-8") as f:
        tests = json.load(f)

    results = []
    for item in tests:
        cat = normalize_category(item.get("category"))
        if cat is None:
            raise ValueError(f"Unknown category in prompts file: {item.get('category')}")

        response, meta = engine.generate(
            item["prompt"],
            max_new_tokens=args.max_new_tokens,
            return_meta=True,
        )
        results.append({
            "category": cat,
            "expected_behavior": EXPECTED[cat],
            "prompt": item["prompt"],
            "response": response.strip(),
            "meta": meta,
        })

    with open(args.output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"Evaluation completed → {args.output_file}")


if __name__ == "__main__":
    main()
