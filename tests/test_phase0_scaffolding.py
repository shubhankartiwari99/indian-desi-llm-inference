import json
import os
import subprocess
import sys
from pathlib import Path

from app.voice.rotation_memory import RotationMemory
from app.voice.state import SessionVoiceState
from app.voice.select import select_voice_variants
from app.voice.contract_loader import get_variants_for


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER = REPO_ROOT / "run_b3_2_eval.py"
BASELINE_PATH = REPO_ROOT / "tests" / "baselines" / "phase0_eval_baseline.json"
OUT_PATH = Path("/tmp/results_b3_2.json")


def test_session_voice_state_roundtrip():
    memory = RotationMemory()
    state = SessionVoiceState(rotation_memory=memory)

    state.escalation_state = "latched"
    state.latched_theme = "family"
    state.emotional_turn_index = 3
    state.selector_invocation_count = 5
    state.last_skeleton = "B"
    state.last_intent = "emotional"
    state.last_emotional_lang = "en"

    state.reset()

    assert state.escalation_state == "none"
    assert state.latched_theme is None
    assert state.emotional_turn_index == 0
    assert state.selector_invocation_count == 0
    assert state.last_skeleton is None
    assert state.last_intent is None
    assert state.last_emotional_lang is None

    as_dict = state.to_dict()
    assert as_dict["rotation_memory"] == {"pools": {}}
    assert as_dict["escalation_state"] == "none"
    assert as_dict["latched_theme"] is None
    assert as_dict["emotional_turn_index"] == 0
    assert as_dict["selector_invocation_count"] == 0
    assert as_dict["last_skeleton"] is None
    assert as_dict["last_intent"] is None
    assert as_dict["last_emotional_lang"] is None


def test_rotation_memory_records_usage():
    memory = RotationMemory()
    assert memory.read_window(("A", "en", "opener")) == []
    memory.record_usage(("A", "en", "opener"), 0, 1)
    snapshot = memory.to_dict()
    assert "A|en|opener" in snapshot["pools"]
    assert snapshot["pools"]["A|en|opener"] == [{"variant_id": 0, "turn_index": 1}]


def test_selector_phase3b_first_turn_is_stable_and_writes_memory():
    state = SessionVoiceState(rotation_memory=RotationMemory())
    state.emotional_turn_index = 1
    selected = select_voice_variants(state, "A", "en")
    assert selected["opener"] == get_variants_for("A", "en", "opener")[0]
    assert selected["validation"] == get_variants_for("A", "en", "validation")[0]
    assert selected["closure"] == get_variants_for("A", "en", "closure")[0]
    pools = state.rotation_memory.to_dict()["pools"]
    assert "A|en|opener" in pools
    assert "A|en|validation" in pools
    assert "A|en|closure" in pools
    assert state.selector_invocation_count == 1


def test_phase0_eval_outputs_unchanged():
    assert BASELINE_PATH.exists(), "Missing Phase 0 baseline file"
    env = os.environ.copy()
    env["TRANSFORMERS_OFFLINE"] = "1"
    env["HF_HUB_OFFLINE"] = "1"
    env["PYTHONPATH"] = str(REPO_ROOT)
    subprocess.check_call([sys.executable, str(RUNNER)], cwd=str(REPO_ROOT), env=env)
    assert OUT_PATH.exists(), "Expected results at /tmp/results_b3_2.json"

    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    current = json.loads(OUT_PATH.read_text(encoding="utf-8"))
    assert len(current.get("sequences", [])) == len(baseline.get("sequences", []))

    for b_seq, c_seq in zip(baseline["sequences"], current["sequences"]):
        assert b_seq["id"] == c_seq["id"]
        assert len(c_seq["turns"]) == len(b_seq["turns"])
        for b_turn, c_turn in zip(b_seq["turns"], c_seq["turns"]):
            # Regression contract: wording must match the locked baseline snapshot.
            assert c_turn["response"] == b_turn["response"]
