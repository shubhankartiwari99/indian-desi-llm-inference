"""
R2 - Manifest & Snapshot Integrity Lock.

Validates that release artifacts are mutually consistent and untampered.
Outputs a deterministic JSON report and exits non-zero on failure.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Dict, List, Tuple

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.model_loader import get_model_dir
from scripts.artifact_digest import get_deterministic_json, get_sha256_digest
from scripts.model_fingerprint import compute_model_fingerprint


VALIDATOR_VERSION = "R3.0"
OPTIONAL_ALLOWED_ARTIFACTS = {"ENGINE_BASELINE_REPLAY.txt", "CONTRACT_FINGERPRINT_LOCK.txt"}


def _canonical_json_bytes(data: Dict) -> bytes:
    return get_deterministic_json(data).encode("utf-8")


def _read_json(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_bytes(content: bytes) -> str:
    return get_sha256_digest(content.decode("utf-8"))


def _validate_manifest_canonical(manifest_path: Path, manifest_data: Dict) -> List[str]:
    errors: List[str] = []
    raw_bytes = manifest_path.read_bytes()
    canonical_bytes = _canonical_json_bytes(manifest_data)
    if raw_bytes != canonical_bytes:
        errors.append("manifest_not_canonical")
    return errors


def _validate_manifest_digest(manifest_data: Dict) -> List[str]:
    errors: List[str] = []
    artifact_digests = manifest_data.get("artifact_digests", {})
    manifest_digest = artifact_digests.get("release_manifest.json")
    if not manifest_digest:
        errors.append("manifest_digest_missing")
        return errors

    manifest_copy = dict(manifest_data)
    manifest_copy["artifact_digests"] = dict(artifact_digests)
    manifest_copy["artifact_digests"].pop("release_manifest.json", None)
    expected_digest = get_sha256_digest(get_deterministic_json(manifest_copy))
    if expected_digest != manifest_digest:
        errors.append("manifest_digest_mismatch")
    return errors


def _validate_contract_snapshot(contract_path: Path, manifest_data: Dict) -> Tuple[List[str], Dict]:
    errors: List[str] = []
    contract_data = _read_json(contract_path)
    contract_fingerprint = contract_data.get("contract_fingerprint")
    contract_raw = contract_data.get("contract_raw_canonical")
    if not contract_fingerprint or contract_raw is None:
        errors.append("contract_snapshot_missing_fields")
        return errors, contract_data

    try:
        raw_contract_obj = json.loads(contract_raw)
    except json.JSONDecodeError:
        errors.append("contract_raw_invalid_json")
        return errors, contract_data

    canonical_raw = get_deterministic_json(raw_contract_obj)
    if canonical_raw != contract_raw:
        errors.append("contract_raw_not_canonical")

    expected_fingerprint = get_sha256_digest(contract_raw)
    if expected_fingerprint != contract_fingerprint:
        errors.append("contract_fingerprint_mismatch")

    manifest_fingerprint = manifest_data.get("contract_fingerprint")
    if manifest_fingerprint and manifest_fingerprint != contract_fingerprint:
        errors.append("manifest_contract_fingerprint_mismatch")

    return errors, contract_data


def _validate_selector_snapshot(selector_path: Path, manifest_data: Dict) -> Tuple[List[str], Dict]:
    errors: List[str] = []
    selector_data = json.loads(selector_path.read_text(encoding="utf-8"))
    selector_digest = get_sha256_digest(get_deterministic_json(selector_data))
    manifest_digest = manifest_data.get("selector_snapshot_digest")
    if manifest_digest and selector_digest != manifest_digest:
        errors.append("selector_snapshot_digest_mismatch")
    return errors, selector_data


def _validate_artifact_digests(artifact_dir: Path, manifest_data: Dict) -> Tuple[List[str], int]:
    errors: List[str] = []
    artifact_digests = manifest_data.get("artifact_digests", {})
    manifest_keys = set(artifact_digests.keys())
    actual_files = {p.name for p in artifact_dir.iterdir() if p.is_file()}

    missing = manifest_keys - actual_files
    extra = (actual_files - manifest_keys) - OPTIONAL_ALLOWED_ARTIFACTS
    for name in sorted(missing):
        errors.append(f"missing_artifact:{name}")
    for name in sorted(extra):
        errors.append(f"extra_artifact:{name}")

    for name in sorted(manifest_keys & actual_files):
        if name == "release_manifest.json":
            continue
        actual_digest = _sha256_bytes((artifact_dir / name).read_bytes())
        if actual_digest != artifact_digests.get(name):
            errors.append(f"artifact_digest_mismatch:{name}")

    return errors, len(manifest_keys)


def _bundle_digest(manifest_data: Dict) -> str:
    artifact_digests = manifest_data.get("artifact_digests", {})
    payload = {
        "artifact_digests": artifact_digests,
        "model_fingerprint": manifest_data.get("model_fingerprint"),
    }
    digest = get_sha256_digest(get_deterministic_json(payload))
    return f"sha256:{digest}"


def _validate_model_fingerprint(
    manifest_data: Dict,
    contract_data: Dict | None,
    selector_data: Dict | None,
    mode: str,
) -> List[str]:
    errors: List[str] = []
    manifest_fp = manifest_data.get("model_fingerprint")
    if not manifest_fp:
        errors.append("model_fingerprint_missing_in_manifest")

    contract_fp = contract_data.get("model_fingerprint") if contract_data else None
    if not contract_fp:
        errors.append("model_fingerprint_missing_in_contract_snapshot")

    selector_fp = selector_data.get("model_fingerprint") if selector_data else None
    if not selector_fp:
        errors.append("model_fingerprint_missing_in_selector_snapshot")

    if manifest_fp and contract_fp and selector_fp:
        if not (manifest_fp == contract_fp == selector_fp):
            errors.append("model_fingerprint_mismatch_across_artifacts")

    if mode == "hard" and manifest_fp:
        live_fp = compute_model_fingerprint(get_model_dir())
        if live_fp != manifest_fp:
            errors.append("model_fingerprint_runtime_mismatch")

    return errors


def validate_bundle(artifact_dir: Path, mode: str) -> Dict:
    errors: List[str] = []
    manifest_path = artifact_dir / "release_manifest.json"
    if not manifest_path.exists():
        errors.append("missing_artifact:release_manifest.json")
        return {
            "manifest_validator_version": VALIDATOR_VERSION,
            "status": "FAIL",
            "errors": errors,
            "artifact_count": 0,
            "bundle_digest": "sha256:0",
        }

    manifest_data = _read_json(manifest_path)
    errors.extend(_validate_manifest_canonical(manifest_path, manifest_data))
    errors.extend(_validate_manifest_digest(manifest_data))

    artifact_errors, artifact_count = _validate_artifact_digests(artifact_dir, manifest_data)
    errors.extend(artifact_errors)

    contract_path = artifact_dir / "contract_snapshot.json"
    contract_data = None
    if contract_path.exists():
        contract_errors, contract_data = _validate_contract_snapshot(contract_path, manifest_data)
        errors.extend(contract_errors)

    selector_path = artifact_dir / "selector_snapshot.json"
    selector_data = None
    if selector_path.exists():
        selector_errors, selector_data = _validate_selector_snapshot(selector_path, manifest_data)
        errors.extend(selector_errors)

    errors.extend(_validate_model_fingerprint(manifest_data, contract_data, selector_data, mode))

    status = "PASS" if not errors else "FAIL"
    return {
        "manifest_validator_version": VALIDATOR_VERSION,
        "status": status,
        "errors": errors,
        "artifact_count": artifact_count,
        "bundle_digest": _bundle_digest(manifest_data) if manifest_data else "sha256:0",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate release manifest integrity")
    parser.add_argument("--artifact-dir", default=str(project_root / "artifacts"))
    parser.add_argument("--mode", default="soft", choices=["soft", "hard"])
    parser.add_argument("--output-file", default=None)
    args = parser.parse_args()

    artifact_dir = Path(args.artifact_dir)
    report = validate_bundle(artifact_dir, args.mode)
    report_json = get_deterministic_json(report)

    if args.output_file:
        Path(args.output_file).write_text(report_json, encoding="utf-8")

    print(report_json)
    if report["status"] != "PASS":
        sys.exit(1)


if __name__ == "__main__":
    main()
