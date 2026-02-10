import json
import subprocess
from pathlib import Path

from app.intent import detect_intent


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER = REPO_ROOT / "run_b3_2_eval.py"
OUT_PATH = Path("/tmp/results_b3_2.json")
PROMPTS_PATH = REPO_ROOT / "eval" / "prompts_b3_1.json"
MODEL_DIR = REPO_ROOT / "artifacts" / "alignment_lora" / "final"
FALLBACK_MODEL_DIR = REPO_ROOT / "artifacts" / "plain_mt5"


def test_family_theme_never_calls_model():
    if not MODEL_DIR.exists() and not FALLBACK_MODEL_DIR.exists():
        print("SKIP: missing model artifacts; skipping family theme invariant test")
        return
    # Run the runner to produce fresh results.
    subprocess.check_call(["python3", str(RUNNER)], cwd=str(REPO_ROOT))

    assert OUT_PATH.exists(), f"Expected results at {OUT_PATH}"
    results = json.loads(OUT_PATH.read_text(encoding="utf-8"))
    prompts = json.loads(PROMPTS_PATH.read_text(encoding="utf-8"))

    # Build a mapping from seq id -> prompt turns for intent detection
    prompts_by_id = {s["id"]: s for s in prompts.get("sequences", [])}

    for seq in results.get("sequences", []):
        seq_id = seq.get("id")
        turns = seq.get("turns", [])

        # Find first turn where emotional_theme == 'family'
        latched_index = None
        for i, t in enumerate(turns):
            meta = t.get("meta", {})
            if meta.get("emotional_theme") == "family":
                latched_index = i
                break

        if latched_index is None:
            continue

        # For all subsequent emotional turns, enforce invariants
        prompt_seq = prompts_by_id.get(seq_id, {})
        prompt_turns = prompt_seq.get("turns", [])
        for j in range(latched_index, len(turns)):
            user_text = prompt_turns[j]
            intent = detect_intent(user_text)
            if intent != "emotional":
                continue
            meta = turns[j].get("meta", {})
            assert meta.get("source") == "escalation_forced", f"Turn {j+1} in {seq_id} not forced"
            assert meta.get("shape") == "emotional_escalation", f"Turn {j+1} in {seq_id} wrong shape"
            assert meta.get("emotional_skeleton") in {"B", "C"}, f"Turn {j+1} in {seq_id} wrong skeleton"
            assert meta.get("source") != "model", f"Turn {j+1} in {seq_id} used raw model"
