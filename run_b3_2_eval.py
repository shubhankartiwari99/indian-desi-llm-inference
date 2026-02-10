from pathlib import Path
import os
import sys
import json

# Ensure repo imports work (workspace root)
REPO_ROOT = Path(__file__).resolve().parent
sys.path.append(str(REPO_ROOT))

from app.inference import InferenceEngine

MODEL_DIR = Path(os.environ.get("MODEL_DIR", "artifacts/plain_mt5"))

PROMPTS_PATH = REPO_ROOT / "eval" / "prompts_b3_1.json"
OUT_PATH = Path("/tmp/results_b3_2.json")

assert PROMPTS_PATH.exists(), f"Missing prompts file: {PROMPTS_PATH}"

with open(PROMPTS_PATH, encoding="utf-8") as f:
    data = json.load(f)

results = {"sequences": []}

for seq in data.get("sequences", []):
    seq_id = seq.get("id")
    turns = seq.get("turns", [])
    engine = InferenceEngine(str(MODEL_DIR))
    seq_res = {"id": seq_id, "turns": []}
    for i, user in enumerate(turns, start=1):
        try:
            resp, meta = engine.generate(user, max_new_tokens=128, return_meta=True)
        except Exception as e:
            resp = ""
            meta = {"error": str(e)}
        seq_res["turns"].append({
            "turn_index": i,
            "user": user,
            "response": resp.strip(),
            "meta": meta,
        })
    results["sequences"].append(seq_res)

with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"Wrote: {OUT_PATH}")
