from __future__ import annotations

import json
from pathlib import Path

from scripts.artifact_digest import get_deterministic_json, get_sha256_digest


def test_contract_fingerprint_lock():
    lock_path = Path("artifacts/CONTRACT_FINGERPRINT_LOCK.txt")
    expected_fingerprint = lock_path.read_text(encoding="utf-8").strip()

    contract_path = Path("docs/persona/voice_contract.json")
    contract_data = json.loads(contract_path.read_text(encoding="utf-8"))
    canonical_contract = get_deterministic_json(contract_data)
    actual_fingerprint = get_sha256_digest(canonical_contract)

    assert actual_fingerprint == expected_fingerprint, (
        "Contract fingerprint drift detected. "
        "Contract content has changed."
    )
