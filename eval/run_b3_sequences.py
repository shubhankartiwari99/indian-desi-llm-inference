if __name__ == "__main__" and __package__ is None:
    from pathlib import Path
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[1]))

import argparse
import json
from pathlib import Path

from app.inference import InferenceEngine
from app.intent import detect_intent
from app.language import detect_language


def parse_args():
    p = argparse.ArgumentParser(description="Run B3 multi-turn sequences and capture persona meta.")
    p.add_argument("--model-dir", default="artifacts/alignment_lora/final")
    p.add_argument("--prompts-file", default="eval/prompts_b3_1.json")
    p.add_argument("--output-file", default="eval/results_b3_1.json")
    p.add_argument("--max-new-tokens", type=int, default=128)
    p.add_argument("--reset-between-sequences", action="store_true", default=True)
    return p.parse_args()


def reset_persona_state(engine: InferenceEngine):
    # Reset only the persona/session state; keep model/memory loaded.
    engine._emo_last_skeleton = None
    engine._emo_last_opener = {}
    engine._emo_last_action_id = None


def load_sequences(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "sequences" in data:
        return data.get("sequences", [])
    if isinstance(data, list):
        return data
    raise ValueError("Unsupported prompts file format; expected {sequences:[...]} or a list.")


def main():
    args = parse_args()
    engine = InferenceEngine(args.model_dir)

    sequences = load_sequences(Path(args.prompts_file))
    results = []

    for seq in sequences:
        seq_id = seq.get("id") or seq.get("sequence_id") or "seq"
        turns = seq.get("turns") or []

        if args.reset_between_sequences:
            reset_persona_state(engine)

        for i, prompt in enumerate(turns, start=1):
            response, meta = engine.generate(
                prompt,
                max_new_tokens=args.max_new_tokens,
                return_meta=True,
            )
            results.append(
                {
                    "sequence_id": seq_id,
                    "turn": i,
                    "prompt": prompt,
                    "detected_intent": detect_intent(prompt),
                    "detected_language": detect_language(prompt),
                    "response": response,
                    "meta": meta,
                }
            )

    Path(args.output_file).write_text(
        json.dumps(results, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"B3 sequences completed → {args.output_file}")


if __name__ == "__main__":
    main()
