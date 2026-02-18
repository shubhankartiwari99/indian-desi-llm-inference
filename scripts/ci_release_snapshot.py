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
import sys
from typing import Dict, List

# Ensure the app and scripts directories are in the Python path.
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.voice.assembler import assemble_response
from app.voice.contract_loader import get_contract_version, get_loader, get_variants_for
from app.voice.fallbacks import sections_for_skeleton
from app.voice.rotation_memory import RotationMemory
from app.voice.runtime import EmotionalSignals, resolve_emotional_skeleton, update_session_state
from app.voice.select import select_voice_variants
from app.voice.state import SessionVoiceState
from scripts.artifact_digest import get_deterministic_json, get_sha256_digest

# --- Constants ---
ARTIFACTS_DIR = project_root / "artifacts"
CONTRACT_SNAPSHOT_PATH = ARTIFACTS_DIR / "contract_snapshot.json"
SELECTOR_SNAPSHOT_PATH = ARTIFACTS_DIR / "selector_snapshot.json"
RELEASE_MANIFEST_PATH = ARTIFACTS_DIR / "release_manifest.json"

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

    return {
        "contract_version": get_contract_version(),
        "contract_fingerprint": fingerprint,
        "contract_raw_canonical": canonical_contract,
    }


def _create_selector_determinism_snapshot() -> List[Dict[str, object]]:
    if len(SELECTOR_SIGNALS_SEQUENCE) != SELECTOR_DETERMINISM_TURNS:
        raise ValueError("Selector signals sequence length mismatch")

    session_state = SessionVoiceState(rotation_memory=RotationMemory())
    snapshot_records: List[Dict[str, object]] = []

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

    return snapshot_records


def main() -> None:
    print("R1: Generating deterministic release snapshot...")
    ARTIFACTS_DIR.mkdir(exist_ok=True)

    # 1) Contract Snapshot
    contract_snapshot_data = _create_contract_snapshot()
    contract_fingerprint = contract_snapshot_data["contract_fingerprint"]
    contract_snapshot_bytes = _canonical_json_bytes(contract_snapshot_data)
    CONTRACT_SNAPSHOT_PATH.write_bytes(contract_snapshot_bytes)

    # 2) Selector Determinism Snapshot
    selector_snapshot_data = _create_selector_determinism_snapshot()
    selector_snapshot_bytes = _canonical_json_bytes(selector_snapshot_data)
    SELECTOR_SNAPSHOT_PATH.write_bytes(selector_snapshot_bytes)
    selector_snapshot_digest = get_sha256_digest(selector_snapshot_bytes.decode("utf-8"))

    # 3) Manifest (written last)
    contract_snapshot_digest = get_sha256_digest(contract_snapshot_bytes.decode("utf-8"))
    release_manifest_data = {
        "release_schema_version": RELEASE_SCHEMA_VERSION,
        "contract_fingerprint": contract_fingerprint,
        "selector_snapshot_digest": selector_snapshot_digest,
        "artifact_digests": {
            CONTRACT_SNAPSHOT_PATH.name: contract_snapshot_digest,
            SELECTOR_SNAPSHOT_PATH.name: selector_snapshot_digest,
        },
    }

    manifest_bytes_for_digest = _canonical_json_bytes(release_manifest_data)
    manifest_digest = get_sha256_digest(manifest_bytes_for_digest.decode("utf-8"))
    release_manifest_data["artifact_digests"][RELEASE_MANIFEST_PATH.name] = manifest_digest
    RELEASE_MANIFEST_PATH.write_bytes(_canonical_json_bytes(release_manifest_data))

    print("Snapshot generation complete.")
    print(f"  - Contract Fingerprint: {contract_fingerprint}")
    print(f"  - Selector Snapshot Digest: {selector_snapshot_digest}")


if __name__ == "__main__":
    main()