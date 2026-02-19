from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from app import runtime_identity


def _canonical_json(data) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _write_bundle(
    artifact_dir: Path,
    *,
    model_fingerprint: str,
    contract_data: dict,
    tamper_manifest_selector_digest: bool = False,
) -> dict:
    artifact_dir.mkdir(parents=True, exist_ok=True)

    canonical_contract = _canonical_json(contract_data)
    contract_fingerprint = _sha256_text(canonical_contract)

    contract_snapshot = {
        "contract_fingerprint": contract_fingerprint,
        "contract_raw_canonical": canonical_contract,
        "contract_version": contract_data.get("contract_version", "unknown"),
        "model_fingerprint": model_fingerprint,
    }
    selector_snapshot = {
        "model_fingerprint": model_fingerprint,
        "selector_snapshot_version": "R3",
        "turns": [],
    }

    (artifact_dir / "contract_snapshot.json").write_text(_canonical_json(contract_snapshot), encoding="utf-8")
    (artifact_dir / "selector_snapshot.json").write_text(_canonical_json(selector_snapshot), encoding="utf-8")

    contract_digest = _sha256_text(_canonical_json(contract_snapshot))
    selector_digest = _sha256_text(_canonical_json(selector_snapshot))
    if tamper_manifest_selector_digest:
        selector_digest = "0" * 64

    manifest = {
        "artifact_digests": {
            "contract_snapshot.json": contract_digest,
            "selector_snapshot.json": selector_digest,
        },
        "contract_fingerprint": contract_fingerprint,
        "model_fingerprint": model_fingerprint,
        "release_schema_version": "R1.0",
        "selector_snapshot_digest": selector_digest,
    }

    manifest_for_digest = dict(manifest)
    manifest_for_digest["artifact_digests"] = dict(manifest["artifact_digests"])
    manifest_digest = _sha256_text(_canonical_json(manifest_for_digest))
    manifest["artifact_digests"]["release_manifest.json"] = manifest_digest
    (artifact_dir / "release_manifest.json").write_text(_canonical_json(manifest), encoding="utf-8")

    return {
        "contract_fingerprint": contract_fingerprint,
        "model_fingerprint": model_fingerprint,
    }


def _patch_runtime_identity(monkeypatch: pytest.MonkeyPatch, artifact_dir: Path, *, model_fp: str, contract_data: dict) -> None:
    monkeypatch.setattr(runtime_identity, "_ARTIFACT_DIR", artifact_dir)
    monkeypatch.setattr(runtime_identity, "_MANIFEST_PATH", artifact_dir / "release_manifest.json")
    monkeypatch.setattr(runtime_identity, "_CONTRACT_SNAPSHOT_PATH", artifact_dir / "contract_snapshot.json")
    monkeypatch.setattr(runtime_identity, "_SELECTOR_SNAPSHOT_PATH", artifact_dir / "selector_snapshot.json")
    monkeypatch.setattr(runtime_identity, "_VERIFY_ONCE_DONE", False)
    monkeypatch.setattr(
        runtime_identity,
        "_RUNTIME_IDENTITY_CACHE",
        {"status": "UNVERIFIED", "errors": ["runtime_identity_not_verified"]},
    )
    monkeypatch.setattr(runtime_identity, "_compute_model_fingerprint", lambda: model_fp)
    monkeypatch.setattr(runtime_identity, "get_loader", lambda: contract_data)


def test_runtime_identity_happy_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    model_fp = "sha256:" + "1" * 64
    contract_data = {"contract_version": "B4.3.2", "skeletons": {"A": {"en": {"opener": ["I hear you."]}}}}
    _write_bundle(tmp_path, model_fingerprint=model_fp, contract_data=contract_data)
    _patch_runtime_identity(monkeypatch, tmp_path, model_fp=model_fp, contract_data=contract_data)

    runtime_identity.verify_runtime_identity(strict=True)
    identity = runtime_identity.get_runtime_identity()

    assert identity["status"] == "PASS"
    assert identity["errors"] == []


def test_runtime_identity_tamper_manifest_digest_value(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    model_fp = "sha256:" + "2" * 64
    contract_data = {"contract_version": "B4.3.2", "skeletons": {"A": {"en": {"validation": ["That sounds tough."]}}}}
    _write_bundle(
        tmp_path,
        model_fingerprint=model_fp,
        contract_data=contract_data,
        tamper_manifest_selector_digest=True,
    )
    _patch_runtime_identity(monkeypatch, tmp_path, model_fp=model_fp, contract_data=contract_data)

    with pytest.raises(RuntimeError):
        runtime_identity.verify_runtime_identity(strict=True)


def test_runtime_identity_tamper_model_fingerprint_mock(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    manifest_model_fp = "sha256:" + "3" * 64
    live_model_fp = "sha256:" + "4" * 64
    contract_data = {"contract_version": "B4.3.2", "skeletons": {"A": {"en": {"closure": ["I'm here for you."]}}}}
    _write_bundle(tmp_path, model_fingerprint=manifest_model_fp, contract_data=contract_data)
    _patch_runtime_identity(monkeypatch, tmp_path, model_fp=live_model_fp, contract_data=contract_data)

    with pytest.raises(RuntimeError):
        runtime_identity.verify_runtime_identity(strict=True)


def test_runtime_identity_tamper_contract_fingerprint_mock(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    model_fp = "sha256:" + "5" * 64
    contract_data = {"contract_version": "B4.3.2", "skeletons": {"A": {"en": {"opener": ["I hear you."]}}}}
    _write_bundle(tmp_path, model_fingerprint=model_fp, contract_data=contract_data)

    tampered_contract_data = {
        "contract_version": "B4.3.2",
        "skeletons": {"A": {"en": {"opener": ["This text was tampered."]}}},
    }
    _patch_runtime_identity(monkeypatch, tmp_path, model_fp=model_fp, contract_data=tampered_contract_data)

    with pytest.raises(RuntimeError):
        runtime_identity.verify_runtime_identity(strict=True)


def test_runtime_identity_non_strict_returns_error_info_without_raise(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    manifest_model_fp = "sha256:" + "6" * 64
    live_model_fp = "sha256:" + "7" * 64
    contract_data = {"contract_version": "B4.3.2", "skeletons": {"A": {"en": {"opener": ["I hear you."]}}}}
    _write_bundle(tmp_path, model_fingerprint=manifest_model_fp, contract_data=contract_data)
    _patch_runtime_identity(monkeypatch, tmp_path, model_fp=live_model_fp, contract_data=contract_data)

    runtime_identity.verify_runtime_identity(strict=False)
    identity = runtime_identity.get_runtime_identity()

    assert identity["status"] == "FAIL"
    assert identity["errors"]
