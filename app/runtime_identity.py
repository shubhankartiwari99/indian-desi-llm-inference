from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List

from app.model_loader import get_model_dir
from app.voice.contract_loader import get_loader


_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_ARTIFACT_DIR = _PROJECT_ROOT / "artifacts"
_MANIFEST_PATH = _ARTIFACT_DIR / "release_manifest.json"
_CONTRACT_SNAPSHOT_PATH = _ARTIFACT_DIR / "contract_snapshot.json"
_SELECTOR_SNAPSHOT_PATH = _ARTIFACT_DIR / "selector_snapshot.json"

_REQUIRED_MODEL_FILES_ORDER = [
    "config.json",
    "generation_config.json",
    "model.safetensors",
    "tokenizer_config.json",
    "spiece.model",
    "special_tokens_map.json",
]
_OPTIONAL_MODEL_FILES = {"generation_config.json", "special_tokens_map.json"}

_RUNTIME_IDENTITY_CACHE: Dict[str, Any] = {
    "status": "UNVERIFIED",
    "errors": ["runtime_identity_not_verified"],
}
_VERIFY_ONCE_DONE = False


def _deterministic_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"Missing required artifact file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _compute_model_fingerprint() -> str:
    model_dir = get_model_dir()
    if not model_dir.exists():
        raise RuntimeError(f"Model directory does not exist: {model_dir}")

    sha = hashlib.sha256()
    for filename in _REQUIRED_MODEL_FILES_ORDER:
        path = model_dir / filename
        if filename in _OPTIONAL_MODEL_FILES and not path.exists():
            continue
        if filename not in _OPTIONAL_MODEL_FILES and not path.exists():
            raise RuntimeError(f"Missing required model file: {filename}")

        sha.update(filename.encode("utf-8"))
        sha.update(b"\n")
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(8192), b""):
                sha.update(chunk)
        sha.update(b"\n")

    return f"sha256:{sha.hexdigest()}"


def _compute_contract_fingerprint() -> str:
    contract_data = get_loader()
    canonical_contract = _deterministic_json(contract_data)
    return _sha256_text(canonical_contract)


def _compute_bundle_digest(artifact_digests: Dict[str, str], model_fingerprint: str) -> str:
    payload = {
        "artifact_digests": artifact_digests,
        "model_fingerprint": model_fingerprint,
    }
    return f"sha256:{_sha256_text(_deterministic_json(payload))}"


def _verify_manifest_digest(manifest: Dict[str, Any], errors: List[str]) -> None:
    artifact_digests = manifest.get("artifact_digests") or {}
    manifest_digest = artifact_digests.get("release_manifest.json")
    if not manifest_digest:
        errors.append("manifest_digest_missing")
        return

    manifest_copy = dict(manifest)
    manifest_copy["artifact_digests"] = dict(artifact_digests)
    manifest_copy["artifact_digests"].pop("release_manifest.json", None)
    expected = _sha256_text(_deterministic_json(manifest_copy))
    if expected != manifest_digest:
        errors.append("manifest_digest_mismatch")


def _manifest_digest_without_self(manifest: Dict[str, Any]) -> str:
    manifest_copy = dict(manifest)
    artifact_digests = dict(manifest.get("artifact_digests") or {})
    artifact_digests.pop("release_manifest.json", None)
    manifest_copy["artifact_digests"] = artifact_digests
    return _sha256_text(_deterministic_json(manifest_copy))


def _collect_runtime_identity() -> Dict[str, Any]:
    errors: List[str] = []

    manifest = _read_json(_MANIFEST_PATH)
    contract_snapshot = _read_json(_CONTRACT_SNAPSHOT_PATH)
    selector_snapshot = _read_json(_SELECTOR_SNAPSHOT_PATH)

    manifest_artifact_digests = manifest.get("artifact_digests") or {}
    contract_snapshot_digest_live = _sha256_text(_deterministic_json(contract_snapshot))
    selector_snapshot_digest_live = _sha256_text(_deterministic_json(selector_snapshot))
    manifest_digest_live = _manifest_digest_without_self(manifest)

    expected_contract_digest = manifest_artifact_digests.get("contract_snapshot.json")
    expected_selector_digest = manifest_artifact_digests.get("selector_snapshot.json")
    expected_manifest_digest = manifest_artifact_digests.get("release_manifest.json")

    if expected_contract_digest != contract_snapshot_digest_live:
        errors.append("artifact_digest_mismatch:contract_snapshot.json")
    if expected_selector_digest != selector_snapshot_digest_live:
        errors.append("artifact_digest_mismatch:selector_snapshot.json")
    if expected_manifest_digest != manifest_digest_live:
        errors.append("artifact_digest_mismatch:release_manifest.json")

    _verify_manifest_digest(manifest, errors)

    model_fingerprint_live = _compute_model_fingerprint()
    contract_fingerprint_live = _compute_contract_fingerprint()

    manifest_model_fingerprint = manifest.get("model_fingerprint")
    manifest_contract_fingerprint = manifest.get("contract_fingerprint")
    contract_snapshot_model_fingerprint = contract_snapshot.get("model_fingerprint")
    selector_snapshot_model_fingerprint = selector_snapshot.get("model_fingerprint")
    contract_snapshot_contract_fingerprint = contract_snapshot.get("contract_fingerprint")

    if manifest_model_fingerprint != model_fingerprint_live:
        errors.append("model_fingerprint_runtime_mismatch")
    if contract_snapshot_model_fingerprint != model_fingerprint_live:
        errors.append("model_fingerprint_contract_snapshot_mismatch")
    if selector_snapshot_model_fingerprint != model_fingerprint_live:
        errors.append("model_fingerprint_selector_snapshot_mismatch")

    if manifest_contract_fingerprint != contract_fingerprint_live:
        errors.append("contract_fingerprint_runtime_mismatch")
    if contract_snapshot_contract_fingerprint != contract_fingerprint_live:
        errors.append("contract_fingerprint_snapshot_mismatch")

    bundle_digest_manifest = _compute_bundle_digest(
        manifest_artifact_digests,
        manifest_model_fingerprint or "",
    )
    live_artifact_digests = {
        "contract_snapshot.json": contract_snapshot_digest_live,
        "release_manifest.json": manifest_digest_live,
        "selector_snapshot.json": selector_snapshot_digest_live,
    }
    bundle_digest_live = _compute_bundle_digest(live_artifact_digests, model_fingerprint_live)
    if bundle_digest_live != bundle_digest_manifest:
        errors.append("bundle_digest_mismatch")

    status = "PASS" if not errors else "FAIL"
    return {
        "status": status,
        "errors": errors,
        "manifest_model_fingerprint": manifest_model_fingerprint,
        "live_model_fingerprint": model_fingerprint_live,
        "manifest_contract_fingerprint": manifest_contract_fingerprint,
        "live_contract_fingerprint": contract_fingerprint_live,
        "bundle_digest_manifest": bundle_digest_manifest,
        "bundle_digest_live": bundle_digest_live,
    }


def verify_runtime_identity(strict: bool = True) -> None:
    global _RUNTIME_IDENTITY_CACHE, _VERIFY_ONCE_DONE

    if strict and _VERIFY_ONCE_DONE:
        return

    identity = _collect_runtime_identity()
    _RUNTIME_IDENTITY_CACHE = identity

    if identity["status"] != "PASS":
        if strict:
            joined_errors = ", ".join(identity["errors"])
            raise RuntimeError(f"Runtime identity verification failed: {joined_errors}")
        return

    _VERIFY_ONCE_DONE = True


def get_runtime_identity() -> Dict[str, Any]:
    return dict(_RUNTIME_IDENTITY_CACHE)
