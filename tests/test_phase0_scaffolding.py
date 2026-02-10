import json
import subprocess
import sys
from pathlib import Path

from app.voice.rotation_memory import RotationMemory
from app.voice.state import SessionVoiceState
from app.voice.select import select_voice_variants


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
    state.last_skeleton = "B"

    state.reset()

    assert state.escalation_state == "none"
    assert state.latched_theme is None
    assert state.emotional_turn_index == 0
    assert state.last_skeleton is None

    as_dict = state.to_dict()
    assert as_dict["rotation_memory"] == {"pools": {}}
    assert as_dict["escalation_state"] == "none"
    assert as_dict["latched_theme"] is None
    assert as_dict["emotional_turn_index"] == 0
    assert as_dict["last_skeleton"] is None


def test_rotation_memory_empty():
    memory = RotationMemory()
    assert memory.read_window(("A", "en", "opener")) == []
    memory.record_usage(("A", "en", "opener"), 0, 1)
    assert memory.to_dict() == {"pools": {}}


def test_selector_stub_raises():
    try:
        select_voice_variants()
    except AssertionError as exc:
        assert "Phase 0" in str(exc)
    else:
        raise AssertionError("select_voice_variants did not raise")


def test_phase0_eval_outputs_unchanged():
    assert BASELINE_PATH.exists(), "Missing Phase 0 baseline file"
    subprocess.check_call([sys.executable, str(RUNNER)], cwd=str(REPO_ROOT))
    assert OUT_PATH.exists(), "Expected results at /tmp/results_b3_2.json"

    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    current = json.loads(OUT_PATH.read_text(encoding="utf-8"))

    assert current == baseline
