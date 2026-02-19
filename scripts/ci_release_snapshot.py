"""
R1 - Step 2: Creates a deterministic release snapshot.

This script generates a minimal, deterministic release bundle composed of:
- artifacts/contract_snapshot.json
- artifacts/selector_snapshot.json
- artifacts/release_manifest.json

Design Constraints:
- This script may only import from 'app' runtime modules and
    'scripts.artifact_digest' for hashing utilities.
- It must not depend on any other 'scripts/ci_*' modules.
- It must be executable as a standalone script.
"""

from pathlib import Path
import argparse
import subprocess
import sys
from typing import Dict, List

# Ensure the app and scripts directories are in the Python path.
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.model_loader import get_model_dir
from app.voice.assembler import assemble_response
from app.voice.contract_loader import get_contract_version, get_loader, get_variants_for
from app.voice.fallbacks import sections_for_skeleton
from app.voice.rotation_memory import RotationMemory
from app.voice.runtime import EmotionalSignals, resolve_emotional_skeleton, update_session_state
from app.voice.select import select_voice_variants
from app.voice.state import SessionVoiceState
from scripts.artifact_digest import get_deterministic_json, get_sha256_digest
from scripts.model_fingerprint import compute_model_fingerprint

# --- Constants ---
DEFAULT_ARTIFACTS_DIR = project_root / "artifacts"

RELEASE_SCHEMA_VERSION = "R1.0"
SELECTOR_DETERMINISM_TURNS = 12
SELECTOR_DETERMINISM_INPUT = "I feel lost."

SELECTOR_SIGNALS_SEQUENCE: List[EmotionalSignals] = [
    EmotionalSignals(lang_mode="en", wants_action=False, has_overwhelm=False, has_guilt=False, has_resignation=False, theme=None, family_theme=False),
    EmotionalSignals(lang_mode="en", wants_action=False, has_overwhelm=True, has_guilt=False, has_resignation=False, theme=None, family_theme=False),
    EmotionalSignals(lang_mode="en", wants_action=False, has_overwhelm=False, has_guilt=True, has_resignation=False, theme=None, family_theme=False),
    EmotionalSignals(lang_mode="en", wants_action=True, has_overwhelm=False, has_guilt=False, has_resignation=False, theme=None, family_theme=False),
    EmotionalSignals(lang_mode="en", wants_action=False, has_overwhelm=False, has_guilt=False, has_resignation=False, theme=None, family_theme=False),
    EmotionalSignals(lang_mode="en", wants_action=False, has_overwhelm=True, has_guilt=True, has_resignation=False, theme=None, family_theme=False),
    EmotionalSignals(lang_mode="en", wants_action=False, has_overwhelm=False, has_guilt=False, has_resignation=False, theme=None, family_theme=False),
    EmotionalSignals(lang_mode="en", wants_action=False, has_overwhelm=False, has_guilt=False, has_resignation=False, theme=None, family_theme=False),
    EmotionalSignals(lang_mode="en", wants_action=True, has_overwhelm=True, has_guilt=False, has_resignation=False, theme=None, family_theme=False),
    EmotionalSignals(lang_mode="en", wants_action=False, has_overwhelm=False, has_guilt=True, has_resignation=False, theme=None, family_theme=False),
    EmotionalSignals(lang_mode="en", wants_action=False, has_overwhelm=False, has_guilt=False, has_resignation=True, theme="resignation", family_theme=False),
    EmotionalSignals(lang_mode="en", wants_action=False, has_overwhelm=False, has_guilt=False, has_resignation=False, theme=None, family_theme=True),
]


# --- Core Snapshot Generation Logic ---

def _canonical_json_bytes(data) -> bytes:
    return get_deterministic_json(data).encode("utf-8")


def _create_contract_snapshot() -> Dict[str, str]:
    contract_data = get_loader()
    canonical_contract = get_deterministic_json(contract_data)
    fingerprint = get_sha256_digest(canonical_contract)
    model_fingerprint = compute_model_fingerprint(get_model_dir())

    return {
        "contract_version": get_contract_version(),
        "contract_fingerprint": fingerprint,
        "model_fingerprint": model_fingerprint,
        "contract_raw_canonical": canonical_contract,
    }


def _create_selector_determinism_snapshot() -> Dict[str, object]:
    if len(SELECTOR_SIGNALS_SEQUENCE) != SELECTOR_DETERMINISM_TURNS:
        raise ValueError("Selector signals sequence length mismatch")

    session_state = SessionVoiceState(rotation_memory=RotationMemory())
    snapshot_records: List[Dict[str, object]] = []
    model_fingerprint = compute_model_fingerprint(get_model_dir())

    for turn_index in range(SELECTOR_DETERMINISM_TURNS):
        signals = SELECTOR_SIGNALS_SEQUENCE[turn_index]
        resolution = resolve_emotional_skeleton(SELECTOR_DETERMINISM_INPUT, session_state, signals)
        skeleton = resolution.emotional_skeleton or "A"
        language = resolution.emotional_lang

        selected_variants = select_voice_variants(session_state, skeleton, language)
        selected_indices = {}
        for section in sections_for_skeleton(skeleton):
            variants = get_variants_for(skeleton, language, section)
            selected_indices[section] = variants.index(selected_variants[section])

        response_text = assemble_response(skeleton, selected_variants)
        response_digest = get_sha256_digest(response_text)

        snapshot_records.append(
            {
                "turn_index": turn_index,
                "resolved_skeleton": skeleton,
                "selected_variant_indices": selected_indices,
                "response_digest": response_digest,
            }
        )

        update_session_state(session_state, SELECTOR_DETERMINISM_INPUT, resolution)

    return {
        "selector_snapshot_version": "R3",
        "model_fingerprint": model_fingerprint,
        "turns": snapshot_records,
    }


def _parse_args():
    parser = argparse.ArgumentParser(description="Generate deterministic release snapshot")
    parser.add_argument("--artifact-dir", default=str(DEFAULT_ARTIFACTS_DIR))
    parser.add_argument("--results-file", default=None)
    return parser.parse_args()


def _run_manifest_validator(artifact_dir: Path) -> None:
    validator_path = project_root / "scripts" / "ci_manifest_validator.py"
    result = subprocess.run(
        [sys.executable, str(validator_path), "--artifact-dir", str(artifact_dir)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("Manifest validation failed.")
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
        sys.exit(result.returncode)


def main() -> None:
    args = _parse_args()
    artifact_dir = Path(args.artifact_dir)

    print("R1: Generating deterministic release snapshot...")
    artifact_dir.mkdir(exist_ok=True)

    # 1) Contract Snapshot
    contract_snapshot_data = _create_contract_snapshot()
    contract_fingerprint = contract_snapshot_data["contract_fingerprint"]
    contract_snapshot_bytes = _canonical_json_bytes(contract_snapshot_data)
    contract_snapshot_path = artifact_dir / "contract_snapshot.json"
    selector_snapshot_path = artifact_dir / "selector_snapshot.json"
    release_manifest_path = artifact_dir / "release_manifest.json"

    contract_snapshot_path.write_bytes(contract_snapshot_bytes)

    # 2) Selector Determinism Snapshot
    selector_snapshot_data = _create_selector_determinism_snapshot()
    selector_snapshot_bytes = _canonical_json_bytes(selector_snapshot_data)
    selector_snapshot_path.write_bytes(selector_snapshot_bytes)
    selector_snapshot_digest = get_sha256_digest(selector_snapshot_bytes.decode("utf-8"))

    # 3) Manifest (written last)
    contract_snapshot_digest = get_sha256_digest(contract_snapshot_bytes.decode("utf-8"))
    model_fingerprint = contract_snapshot_data["model_fingerprint"]
    release_manifest_data = {
        "release_schema_version": RELEASE_SCHEMA_VERSION,
        "contract_fingerprint": contract_fingerprint,
        "selector_snapshot_digest": selector_snapshot_digest,
        "model_fingerprint": model_fingerprint,
        "artifact_digests": {
            contract_snapshot_path.name: contract_snapshot_digest,
            selector_snapshot_path.name: selector_snapshot_digest,
        },
    }

    manifest_bytes_for_digest = _canonical_json_bytes(release_manifest_data)
    manifest_digest = get_sha256_digest(manifest_bytes_for_digest.decode("utf-8"))
    release_manifest_data["artifact_digests"][release_manifest_path.name] = manifest_digest
    release_manifest_path.write_bytes(_canonical_json_bytes(release_manifest_data))

    _run_manifest_validator(artifact_dir)

    print("Snapshot generation complete.")
    print(f"  - Contract Fingerprint: {contract_fingerprint}")
    print(f"  - Selector Snapshot Digest: {selector_snapshot_digest}")


if __name__ == "__main__":
    main()