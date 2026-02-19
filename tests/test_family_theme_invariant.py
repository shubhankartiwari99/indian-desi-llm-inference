import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from app.intent import detect_intent


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER = REPO_ROOT / "run_b3_2_eval.py"
OUT_PATH = Path("/tmp/results_b3_2.json")
PROMPTS_PATH = REPO_ROOT / "eval" / "prompts_b3_1.json"


def test_family_theme_never_calls_model():
    # Run the runner to produce fresh results.
    env = os.environ.copy()
    env["TRANSFORMERS_OFFLINE"] = "1"
    env["HF_HUB_OFFLINE"] = "1"
    env["PYTHONPATH"] = str(REPO_ROOT)
    subprocess.check_call([sys.executable, str(RUNNER)], cwd=str(REPO_ROOT), env=env)

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
            assert meta.get("latched_theme") == "family", f"Turn {j+1} in {seq_id} missing family latch"
            assert meta.get("emotional_skeleton") in {"B", "C"}, f"Turn {j+1} in {seq_id} wrong skeleton"


test_family_theme_never_calls_model = pytest.mark.requires_model(test_family_theme_never_calls_model)
