"""Tests for the ci_release_snapshot script."""

from __future__ import annotations

import contextlib
import json
from pathlib import Path
import subprocess
import sys

from app.voice.assembler import assemble_response
from app.voice.rotation_memory import RotationMemory
from app.voice.runtime import resolve_emotional_skeleton, update_session_state
from app.voice.select import select_voice_variants
from app.voice.state import SessionVoiceState
from scripts import ci_release_snapshot
from scripts.artifact_digest import get_deterministic_json, get_sha256_digest

ARTIFACT_FILES = (
    "contract_snapshot.json",
    "selector_snapshot.json",
    "release_manifest.json",
)


@contextlib.contextmanager
def _preserve_artifacts():
    artifacts_dir = Path("artifacts")
    dir_existed = artifacts_dir.exists()
    prior_contents = {}
    if dir_existed:
        for name in ARTIFACT_FILES:
            path = artifacts_dir / name
            if path.exists():
                prior_contents[name] = path.read_bytes()

    try:
        yield
    finally:
        artifacts_dir = Path("artifacts")
        if not dir_existed:
            for name in ARTIFACT_FILES:
                path = artifacts_dir / name
                if path.exists():
                    path.unlink()
            if artifacts_dir.exists() and not any(artifacts_dir.iterdir()):
                artifacts_dir.rmdir()
            return

        artifacts_dir.mkdir(exist_ok=True)
        for name in ARTIFACT_FILES:
            path = artifacts_dir / name
            if name in prior_contents:
                path.write_bytes(prior_contents[name])
            elif path.exists():
                path.unlink()


def _run_snapshot_script():
    subprocess.run(
        [sys.executable, "scripts/ci_release_snapshot.py"],
        check=True,
        cwd=Path.cwd(),
        env={"PYTHONPATH": str(Path.cwd())},
    )


def test_release_snapshot_deterministic_bytes():
    """Verify that two runs of the script produce byte-identical artifacts."""
    with _preserve_artifacts():
        _run_snapshot_script()
        run1_contents = {}
        for name in ARTIFACT_FILES:
            run1_contents[name] = (Path("artifacts") / name).read_bytes()

        _run_snapshot_script()
        for name in ARTIFACT_FILES:
            assert run1_contents[name] == (Path("artifacts") / name).read_bytes()


def test_contract_fingerprint_stable():
    """Verify that the contract fingerprint is stable and computed correctly."""
    with _preserve_artifacts():
        _run_snapshot_script()

        snapshot = json.loads((Path("artifacts") / "contract_snapshot.json").read_text(encoding="utf-8"))
        fingerprint_from_snapshot = snapshot["contract_fingerprint"]

        contract_data = json.loads(Path("docs/persona/voice_contract.json").read_text(encoding="utf-8"))
        canonical_contract = get_deterministic_json(contract_data)
        manual_fingerprint = get_sha256_digest(canonical_contract)

        assert fingerprint_from_snapshot == manual_fingerprint


def test_selector_snapshot_replay_identity():
    """Verify that an in-memory replay matches the snapshot's digests."""
    with _preserve_artifacts():
        _run_snapshot_script()

        turns_from_snapshot = json.loads(
            (Path("artifacts") / "selector_snapshot.json").read_text(encoding="utf-8")
        )

        session_state = SessionVoiceState(rotation_memory=RotationMemory())

        for turn_index in range(ci_release_snapshot.SELECTOR_DETERMINISM_TURNS):
            signals = ci_release_snapshot.SELECTOR_SIGNALS_SEQUENCE[turn_index]
            resolution = resolve_emotional_skeleton(
                ci_release_snapshot.SELECTOR_DETERMINISM_INPUT,
                session_state,
                signals,
            )
            skeleton = resolution.emotional_skeleton or "A"
            language = resolution.emotional_lang

            selected_variants = select_voice_variants(session_state, skeleton, language)
            response_text = assemble_response(skeleton, selected_variants)
            response_digest = get_sha256_digest(response_text)

            assert turns_from_snapshot[turn_index]["response_digest"] == response_digest
            update_session_state(session_state, ci_release_snapshot.SELECTOR_DETERMINISM_INPUT, resolution)


def test_manifest_integrity_links():
    """Verify that all files in the manifest match their listed digests."""
    with _preserve_artifacts():
        _run_snapshot_script()

        manifest = json.loads(
            (Path("artifacts") / "release_manifest.json").read_text(encoding="utf-8")
        )

        for filename, digest_from_manifest in manifest["artifact_digests"].items():
            if filename == "release_manifest.json":
                manifest_copy = dict(manifest)
                manifest_copy["artifact_digests"] = dict(manifest_copy["artifact_digests"])
                del manifest_copy["artifact_digests"]["release_manifest.json"]
                manifest_without_digest = get_deterministic_json(manifest_copy)
                actual_digest = get_sha256_digest(manifest_without_digest)
                assert actual_digest == digest_from_manifest
            else:
                actual_digest = get_sha256_digest(
                    (Path("artifacts") / filename).read_text(encoding="utf-8")
                )
                assert actual_digest == digest_from_manifest
